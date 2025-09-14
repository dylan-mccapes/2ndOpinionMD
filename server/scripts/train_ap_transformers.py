import os, json, argparse, numpy as np
from datasets import load_dataset
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          DataCollatorWithPadding, Trainer, TrainingArguments)
import evaluate

LABELS4 = ["Direct","Indirect","Neither","Not Relevant"]
MAP4 = {l:i for i,l in enumerate(LABELS4)}

def load_jsonl_dataset(path, text_a, text_b, label_field, labels_map):
    return load_dataset("json", data_files=path, split="train").map(
        lambda ex: {
            "text_a": ex[text_a],
            "text_b": ex[text_b],
            "label": labels_map[ex[label_field]]
        } if labels_map else {
            "text_a": ex[text_a],
            "text_b": ex[text_b],
            "label": 1 if ex[label_field] in ("related", True, 1) else 0
        }
    )

def tokenize_fn(examples, tokenizer, max_len):
    return tokenizer(examples["text_a"], examples["text_b"],
                     truncation=True, max_length=max_len)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["silver","gold"], required=True)
    ap.add_argument("--model_name", default="roberta-base")
    ap.add_argument("--tokenizer_name", default="roberta-base")
    ap.add_argument("--silver", default="data/silver_balanced.jsonl")
    ap.add_argument("--gold_train", default="data/gold_train.jsonl")
    ap.add_argument("--gold_dev",   default="data/gold_dev.jsonl")
    ap.add_argument("--gold_test",  default="data/gold_test.jsonl")
    ap.add_argument("--out_dir", default="models/ap_ce")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--max_len", type=int, default=384)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    import os
    tok_src = args.model_name if (os.path.isdir(args.model_name) and os.path.exists(os.path.join(args.model_name,'tokenizer_config.json'))) else args.tokenizer_name
    tokenizer = AutoTokenizer.from_pretrained(tok_src, use_fast=True)

    if args.stage == "silver":
        train_ds = load_jsonl_dataset(args.silver, "assessment", "plan_item", "label", labels_map=None)
        eval_ds  = train_ds.select(range(min(2000, len(train_ds))))  # quick sanity eval
        num_labels = 2
        id2label = {0:"not", 1:"related"}
        label2id = {"not":0, "related":1}
        out_dir = os.path.join(args.out_dir, "silver")
    else:
        train_ds = load_jsonl_dataset(args.gold_train, "assessment", "plan_item", "label", labels_map=MAP4)
        eval_ds  = load_jsonl_dataset(args.gold_dev,   "assessment", "plan_item", "label", labels_map=MAP4)
        num_labels = 4
        id2label = {i:l for l,i in MAP4.items()}
        label2id = MAP4
        out_dir = os.path.join(args.out_dir, "gold")

    tokenized_train = train_ds.map(lambda ex: tokenize_fn(ex, tokenizer, args.max_len), batched=True, remove_columns=train_ds.column_names)
    tokenized_eval  = eval_ds.map( lambda ex: tokenize_fn(ex, tokenizer, args.max_len), batched=True, remove_columns=eval_ds.column_names)

    # init model (for gold, you likely pass --model_name models/ap_ce/silver/best)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name, num_labels=num_labels, id2label=id2label, label2id=label2id
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    metric_acc = evaluate.load("accuracy")
    metric_f1  = evaluate.load("f1")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        out = {"accuracy": metric_acc.compute(predictions=preds, references=labels)["accuracy"]}
        if num_labels == 4:
            out["macro_f1"] = metric_f1.compute(predictions=preds, references=labels, average="macro")["f1"]
            # per-class F1 (optional)
            for i, name in id2label.items():
                mask = labels==i
                if mask.sum()>0:
                    out[f"f1_{name}"] = metric_f1.compute(predictions=preds[mask], references=labels[mask], average="binary")["f1"]
        else:
            out["f1"] = metric_f1.compute(predictions=preds, references=labels)["f1"]
        return out

    args_train = TrainingArguments(
        output_dir=out_dir,
        learning_rate=args.lr,
        per_device_train_batch_size=args.bsz,
        per_device_eval_batch_size=min(64, args.bsz*2),
        num_train_epochs=args.epochs,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1" if num_labels==4 else "f1",
        greater_is_better=True,
        seed=args.seed,
        report_to=[],
        bf16=False  # bf16 not supported on MPS; keep fp32
    )

    trainer = Trainer(
        model=model,
        args=args_train,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics
    )

    trainer.train()
    trainer.save_model(os.path.join(out_dir, "best"))

    # Optional test set eval (gold only)
    if args.stage == "gold":
        test_ds = load_jsonl_dataset(args.gold_test, "assessment","plan_item","label", labels_map=MAP4)
        tok_test = test_ds.map(lambda ex: tokenize_fn(ex, tokenizer, args.max_len), batched=True, remove_columns=test_ds.column_names)
        test_metrics = trainer.evaluate(tok_test, metric_key_prefix="test")
        with open(os.path.join(out_dir, "test_metrics.json"), "w") as f:
            json.dump(test_metrics, f, indent=2)
        print("TEST:", test_metrics)

if __name__ == "__main__":
    main()
