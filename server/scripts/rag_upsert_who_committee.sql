-- Project WHO Expert Committee Executive Summary into RAG
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT 'who_committee',
       'WHO Committee 2025: ' || left(coalesce(heading,'(untitled)'), 200),
       text,
       to_tsvector('english', coalesce(heading,'')||' '||coalesce(text,''))
FROM guidelines.who_committee_sections s
WHERE NOT EXISTS (
  SELECT 1 FROM public.rag_corpus rc
  WHERE rc.source='who_committee'
    AND rc.title='WHO Committee 2025: '||left(coalesce(s.heading,'(untitled)'),200)
);

