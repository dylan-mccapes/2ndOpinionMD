# server/tests/test_eoh_router.py
"""
Unit tests for the EoH Router.

Tests the MODULE_INDEX, router_llm, and eoh_router_routes modules.
Uses mocked LLM responses to test deterministic behavior.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from server.eoh.module_index import (
    MODULE_INDEX,
    QUESTION_TYPES,
    get_module_ids,
    get_all_doc_handle_names,
    get_modules_for_question_type,
    get_module_index_for_llm,
)
from server.eoh.router_llm import (
    eoh_llm_router,
    create_mock_router_response,
    _validate_and_clean_plan,
    _create_fallback_plan,
)
from server.api.app_postgres import app


client = TestClient(app)


class TestModuleIndex:
    """Tests for the MODULE_INDEX and related functions."""
    
    def test_module_index_has_required_modules(self):
        """Test that MODULE_INDEX contains all modules needed for question types A-E."""
        required_modules = {
            "M1", "M2", "M3A", "M3B", "M4", "M5", "M6", "M7A", "M7B",
            "M9", "M10", "M11", "M12", "M13", "M14", "M15", "M19", "M20",
            "M21", "M22", "M23", "M24", "M25", "M41", "M48"
        }
        actual_modules = set(MODULE_INDEX.keys())
        missing = required_modules - actual_modules
        assert not missing, f"Missing required modules: {missing}"
    
    def test_module_index_structure(self):
        """Test that each module has the required fields."""
        required_fields = {"name", "layer", "llm_use_when", "doc_handles"}
        valid_layers = {"terrain", "signal_tagging", "flare_detection", "care_planning", "governance"}
        
        for mid, mod in MODULE_INDEX.items():
            for field in required_fields:
                assert field in mod, f"Module {mid} missing field: {field}"
            
            assert mod["layer"] in valid_layers, f"Module {mid} has invalid layer: {mod['layer']}"
            assert isinstance(mod["doc_handles"], list), f"Module {mid} doc_handles is not a list"
            
            for handle in mod["doc_handles"]:
                assert "kind" in handle, f"Module {mid} handle missing 'kind'"
                assert "name" in handle, f"Module {mid} handle missing 'name'"
                assert handle["kind"] in {"pg_view", "pg_table", "ann_index", "doc_corpus", "ethos_module_doc"}
    
    def test_question_types_structure(self):
        """Test that QUESTION_TYPES has the correct structure."""
        expected_types = {"A", "B", "C", "D", "E"}
        assert set(QUESTION_TYPES.keys()) == expected_types
        
        for qt, info in QUESTION_TYPES.items():
            assert "description" in info, f"Question type {qt} missing description"
            assert "goal" in info, f"Question type {qt} missing goal"
            assert "canonical_modules" in info, f"Question type {qt} missing canonical_modules"
            assert isinstance(info["canonical_modules"], list)
    
    def test_get_module_ids(self):
        """Test get_module_ids returns all module IDs."""
        ids = get_module_ids()
        assert isinstance(ids, list)
        assert len(ids) == len(MODULE_INDEX)
        assert "M1" in ids
        assert "M13" in ids
    
    def test_get_all_doc_handle_names(self):
        """Test get_all_doc_handle_names returns all handle names."""
        names = get_all_doc_handle_names()
        assert isinstance(names, set)
        assert "eoh_m1_patient_terrain" in names
        assert "eoh_m13_forecasts" in names
    
    def test_get_modules_for_question_type(self):
        """Test get_modules_for_question_type returns correct modules."""
        type_a_modules = get_modules_for_question_type("A")
        assert "M1" in type_a_modules
        assert "M13" in type_a_modules
        
        type_e_modules = get_modules_for_question_type("E")
        assert "M19" in type_e_modules
        assert "M41" in type_e_modules
        assert "M48" in type_e_modules
        
        unknown_modules = get_modules_for_question_type("UNKNOWN")
        assert unknown_modules == []
    
    def test_get_module_index_for_llm(self):
        """Test get_module_index_for_llm returns simplified index."""
        llm_index = get_module_index_for_llm()
        assert isinstance(llm_index, list)
        assert len(llm_index) == len(MODULE_INDEX)
        
        for item in llm_index:
            assert "id" in item
            assert "name" in item
            assert "layer" in item
            assert "llm_use_when" in item
            assert "doc_handles" in item


class TestRouterLLM:
    """Tests for the router_llm module."""
    
    def test_create_fallback_plan(self):
        """Test _create_fallback_plan returns valid structure."""
        plan = _create_fallback_plan()
        assert plan["question_type"] == "OTHER"
        assert "question_type_explanation" in plan
        assert plan["module_plan"] == []
        assert plan["doc_retrieval_plan"] == []
        
        plan_with_type = _create_fallback_plan("A")
        assert plan_with_type["question_type"] == "A"
    
    def test_validate_and_clean_plan_removes_unknown_modules(self):
        """Test that validation removes unknown module IDs."""
        valid_module_ids = {"M1", "M2", "M3A"}
        valid_doc_handles = {"eoh_m1_patient_terrain", "eoh_m2_baseline_drift"}
        
        plan = {
            "question_type": "A",
            "question_type_explanation": "Test",
            "module_plan": [
                {"step": 1, "goal": "Test", "modules": ["M1", "M999", "M2"], "why": "Test"}
            ],
            "doc_retrieval_plan": []
        }
        
        cleaned = _validate_and_clean_plan(plan, valid_module_ids, valid_doc_handles)
        
        assert cleaned["module_plan"][0]["modules"] == ["M1", "M2"]
        assert "M999" not in cleaned["module_plan"][0]["modules"]
    
    def test_validate_and_clean_plan_removes_unknown_handles(self):
        """Test that validation removes unknown doc handles."""
        valid_module_ids = {"M1"}
        valid_doc_handles = {"eoh_m1_patient_terrain"}
        
        plan = {
            "question_type": "A",
            "question_type_explanation": "Test",
            "module_plan": [],
            "doc_retrieval_plan": [
                {
                    "module": "M1",
                    "handles": [
                        {"kind": "pg_view", "name": "eoh_m1_patient_terrain"},
                        {"kind": "pg_view", "name": "unknown_handle"}
                    ],
                    "purpose": "Test"
                }
            ]
        }
        
        cleaned = _validate_and_clean_plan(plan, valid_module_ids, valid_doc_handles)
        
        assert len(cleaned["doc_retrieval_plan"]) == 1
        assert len(cleaned["doc_retrieval_plan"][0]["handles"]) == 1
        assert cleaned["doc_retrieval_plan"][0]["handles"][0]["name"] == "eoh_m1_patient_terrain"
    
    def test_validate_and_clean_plan_fixes_invalid_question_type(self):
        """Test that validation fixes invalid question types."""
        valid_module_ids = set()
        valid_doc_handles = set()
        
        plan = {
            "question_type": "INVALID",
            "question_type_explanation": "Test",
            "module_plan": [],
            "doc_retrieval_plan": []
        }
        
        cleaned = _validate_and_clean_plan(plan, valid_module_ids, valid_doc_handles)
        assert cleaned["question_type"] == "OTHER"
    
    def test_create_mock_router_response_type_a(self):
        """Test mock response for Type A question."""
        response = create_mock_router_response("A")
        
        assert response["question_type"] == "A"
        assert "question_type_explanation" in response
        assert len(response["module_plan"]) > 0
        assert len(response["doc_retrieval_plan"]) > 0
        
        all_modules = []
        for step in response["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M1" in all_modules
        assert "M2" in all_modules
        assert "M13" in all_modules
    
    def test_create_mock_router_response_type_b(self):
        """Test mock response for Type B question."""
        response = create_mock_router_response("B")
        
        assert response["question_type"] == "B"
        
        all_modules = []
        for step in response["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M1" in all_modules
        assert "M4" in all_modules
        assert "M6" in all_modules
    
    def test_create_mock_router_response_type_e(self):
        """Test mock response for Type E question."""
        response = create_mock_router_response("E")
        
        assert response["question_type"] == "E"
        
        all_modules = []
        for step in response["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M19" in all_modules
        assert "M41" in all_modules
        assert "M48" in all_modules
    
    def test_create_mock_router_response_type_other(self):
        """Test mock response for OTHER question type."""
        response = create_mock_router_response("OTHER")
        
        assert response["question_type"] == "OTHER"
        assert response["module_plan"] == []
        assert response["doc_retrieval_plan"] == []
    
    def test_create_mock_router_response_invalid_type(self):
        """Test mock response for invalid question type defaults to OTHER."""
        response = create_mock_router_response("INVALID")
        
        assert response["question_type"] == "OTHER"


class TestMockedLLMRouter:
    """Tests for eoh_llm_router with mocked LLM responses."""
    
    @pytest.mark.asyncio
    async def test_router_type_a_question(self):
        """Test router with Type A flare risk question."""
        mock_response = {
            "question_type": "A",
            "question_type_explanation": "This is a flare risk prediction question",
            "module_plan": [
                {"step": 1, "goal": "Check terrain", "modules": ["M1", "M2", "M3A"], "why": "Baseline assessment"},
                {"step": 2, "goal": "Validate signals", "modules": ["M7A", "M4", "M5", "M9"], "why": "Data quality"},
                {"step": 3, "goal": "Generate forecast", "modules": ["M12", "M13"], "why": "Prognostic analysis"},
                {"step": 4, "goal": "Output plan", "modules": ["M14", "M21", "M24", "M25"], "why": "User communication"}
            ],
            "doc_retrieval_plan": [
                {"module": "M1", "handles": [{"kind": "pg_view", "name": "eoh_m1_patient_terrain"}], "purpose": "Get terrain"},
                {"module": "M13", "handles": [{"kind": "pg_view", "name": "eoh_m13_forecasts"}], "purpose": "Get forecasts"}
            ]
        }
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        )
        
        result = await eoh_llm_router(
            client=mock_client,
            question="What is this patient's flare risk over the next 30 days?"
        )
        
        assert result["question_type"] == "A"
        assert len(result["module_plan"]) > 0
        
        all_modules = []
        for step in result["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M1" in all_modules
        assert "M13" in all_modules
    
    @pytest.mark.asyncio
    async def test_router_type_b_question(self):
        """Test router with Type B real flare vs symbolic question."""
        mock_response = {
            "question_type": "B",
            "question_type_explanation": "This is a flare classification question",
            "module_plan": [
                {"step": 1, "goal": "Locate event", "modules": ["M1", "M2", "M3A"], "why": "Terrain context"},
                {"step": 2, "goal": "Examine signals", "modules": ["M7A", "M12", "M4", "M5"], "why": "Signal analysis"},
                {"step": 3, "goal": "Run suppression reasoning", "modules": ["M4", "M9", "M5"], "why": "Classification"},
                {"step": 4, "goal": "Route outcome", "modules": ["M6", "M11", "M7B", "M10"], "why": "Action routing"}
            ],
            "doc_retrieval_plan": [
                {"module": "M4", "handles": [{"kind": "pg_view", "name": "eoh_m4_suppression_audit"}], "purpose": "Suppression data"}
            ]
        }
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        )
        
        result = await eoh_llm_router(
            client=mock_client,
            question="Is this a real flare or just overshoot / symbolic?"
        )
        
        assert result["question_type"] == "B"
        
        all_modules = []
        for step in result["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M1" in all_modules
        assert "M4" in all_modules
        assert "M6" in all_modules
    
    @pytest.mark.asyncio
    async def test_router_type_e_meta_question(self):
        """Test router with Type E meta-calibration question."""
        mock_response = {
            "question_type": "E",
            "question_type_explanation": "This is a meta/calibration question",
            "module_plan": [
                {"step": 1, "goal": "Check calibration", "modules": ["M19", "M41", "M48"], "why": "System metrics"}
            ],
            "doc_retrieval_plan": [
                {"module": "M19", "handles": [{"kind": "pg_view", "name": "eoh_m19_calibration_metrics"}], "purpose": "Calibration data"}
            ]
        }
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        )
        
        result = await eoh_llm_router(
            client=mock_client,
            question="Is the model still calibrated? Are we over-suppressing flares?"
        )
        
        assert result["question_type"] == "E"
        
        all_modules = []
        for step in result["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M19" in all_modules
        assert "M41" in all_modules
        assert "M48" in all_modules
    
    @pytest.mark.asyncio
    async def test_router_fallback_on_parse_error(self):
        """Test router returns fallback plan on JSON parse error."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="not valid json"))]
        )
        
        result = await eoh_llm_router(
            client=mock_client,
            question="Some question"
        )
        
        assert result["question_type"] == "OTHER"
        assert result["module_plan"] == []
    
    @pytest.mark.asyncio
    async def test_router_validates_only_known_modules(self):
        """Test router drops unknown module IDs from response."""
        mock_response = {
            "question_type": "A",
            "question_type_explanation": "Test",
            "module_plan": [
                {"step": 1, "goal": "Test", "modules": ["M1", "M999", "FAKE_MODULE"], "why": "Test"}
            ],
            "doc_retrieval_plan": []
        }
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        )
        
        result = await eoh_llm_router(
            client=mock_client,
            question="Test question"
        )
        
        all_modules = []
        for step in result["module_plan"]:
            all_modules.extend(step["modules"])
        
        assert "M1" in all_modules
        assert "M999" not in all_modules
        assert "FAKE_MODULE" not in all_modules
    
    @pytest.mark.asyncio
    async def test_router_validates_only_known_doc_handles(self):
        """Test router drops unknown doc handles from response."""
        mock_response = {
            "question_type": "A",
            "question_type_explanation": "Test",
            "module_plan": [],
            "doc_retrieval_plan": [
                {
                    "module": "M1",
                    "handles": [
                        {"kind": "pg_view", "name": "eoh_m1_patient_terrain"},
                        {"kind": "pg_view", "name": "fake_handle_name"}
                    ],
                    "purpose": "Test"
                }
            ]
        }
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        )
        
        result = await eoh_llm_router(
            client=mock_client,
            question="Test question"
        )
        
        assert len(result["doc_retrieval_plan"]) == 1
        handles = result["doc_retrieval_plan"][0]["handles"]
        handle_names = [h["name"] for h in handles]
        
        assert "eoh_m1_patient_terrain" in handle_names
        assert "fake_handle_name" not in handle_names
    
    @pytest.mark.asyncio
    async def test_router_empty_question_raises_error(self):
        """Test router raises ValueError for empty question."""
        mock_client = MagicMock()
        
        with pytest.raises(ValueError, match="Question cannot be empty"):
            await eoh_llm_router(
                client=mock_client,
                question=""
            )


class TestEoHRouterEndpoints:
    """Tests for the EoH router API endpoints."""
    
    def test_get_question_types(self):
        """Test GET /api/eoh/question_types returns all question types."""
        response = client.get("/api/eoh/question_types")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
        
        type_codes = [item["type_code"] for item in data]
        assert "A" in type_codes
        assert "B" in type_codes
        assert "C" in type_codes
        assert "D" in type_codes
        assert "E" in type_codes
    
    def test_get_modules(self):
        """Test GET /api/eoh/modules returns all modules."""
        response = client.get("/api/eoh/modules")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(MODULE_INDEX)
        
        module_ids = [item["id"] for item in data]
        assert "M1" in module_ids
        assert "M13" in module_ids
        assert "M21" in module_ids
    
    def test_get_module_by_id(self):
        """Test GET /api/eoh/modules/{module_id} returns specific module."""
        response = client.get("/api/eoh/modules/M1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "M1"
        assert data["name"] == "Patient Terrain Model"
        assert data["layer"] == "terrain"
        assert "doc_handles" in data
    
    def test_get_module_not_found(self):
        """Test GET /api/eoh/modules/{module_id} returns 404 for unknown module."""
        response = client.get("/api/eoh/modules/M999")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"]["code"] == "module_not_found"
    
    def test_eoh_router_health(self):
        """Test GET /api/eoh/health returns health status."""
        response = client.get("/api/eoh/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "module_count" in data
        assert data["module_count"] == len(MODULE_INDEX)
        assert "question_types" in data
    
    def test_router_plan_empty_question(self):
        """Test POST /api/eoh/router_plan rejects empty question.
        Pydantic min_length=1 on RouterPlanRequest.question returns 422 before
        the route handler's own 400 check fires."""
        response = client.post("/api/eoh/router_plan", json={"question": ""})
        assert response.status_code == 422
    
    def test_router_plan_missing_question(self):
        """Test POST /api/eoh/router_plan rejects missing question."""
        response = client.post("/api/eoh/router_plan", json={})
        assert response.status_code == 422


class TestEoHStreamRouterIntegration:
    """Tests for the EoH stream router integration in rag_stream_custom_endpoints."""
    
    def test_eoh_routed_answer_system_prompt_exists(self):
        """Test that EOH_ROUTED_ANSWER_SYSTEM_PROMPT is defined."""
        from server.api.rag_stream_custom_endpoints import EOH_ROUTED_ANSWER_SYSTEM_PROMPT
        
        assert EOH_ROUTED_ANSWER_SYSTEM_PROMPT is not None
        assert len(EOH_ROUTED_ANSWER_SYSTEM_PROMPT) > 0
        # Prompt uses mixed case: "EoH Router Plan", "EoH router plan"
        assert "eoh router plan" in EOH_ROUTED_ANSWER_SYSTEM_PROMPT.lower()
        assert "question type" in EOH_ROUTED_ANSWER_SYSTEM_PROMPT.lower()
    
    def test_eoh_stream_event_generator_exists(self):
        """Test that eoh_stream_event_generator function is defined."""
        from server.api.rag_stream_custom_endpoints import eoh_stream_event_generator
        
        assert callable(eoh_stream_event_generator)
    
    def test_eoh_router_imports_in_rag_stream(self):
        """Test that EoH router imports are present in rag_stream_custom_endpoints."""
        import server.api.rag_stream_custom_endpoints as module
        
        assert hasattr(module, 'eoh_llm_router')
        assert hasattr(module, 'MODULE_INDEX')
        assert hasattr(module, 'EOH_SYSTEM_PROMPT')
    
    def test_router_plan_context_item_structure(self):
        """Test the structure of a router plan context item."""
        question_type = "A"
        router_plan_text = "EoH question type: A\nExplanation: Test"
        
        router_ctx_item = {
            "source": "eoh_router",
            "source_id": f"eoh_plan:{question_type}",
            "id": f"eoh_router_plan_{question_type}",
            "title": "EoH Router plan (modules + doc handles)",
            "text": router_plan_text,
            "score": 1.0,
            "method": "eoh_router",
        }
        
        assert router_ctx_item["source"] == "eoh_router"
        assert router_ctx_item["score"] == 1.0
        assert "eoh_plan:A" in router_ctx_item["source_id"]
        assert "EoH Router plan" in router_ctx_item["title"]
    
    def test_router_plan_text_formatting(self):
        """Test the formatting of router plan text for context injection."""
        plan = {
            "question_type": "A",
            "question_type_explanation": "Flare risk prediction",
            "module_plan": [
                {"step": 1, "goal": "Check terrain", "modules": ["M1", "M2"], "why": "Baseline"}
            ],
            "doc_retrieval_plan": [
                {"module": "M1", "handles": [{"kind": "pg_view", "name": "eoh_m1_patient_terrain"}], "purpose": "Get terrain"}
            ]
        }
        
        question_type = plan.get("question_type", "OTHER")
        qt_expl = plan.get("question_type_explanation", "")
        
        router_plan_text_lines = [
            f"EoH question type: {question_type}",
            f"Explanation: {qt_expl}",
            "",
            "Module plan:",
        ]
        for step in plan.get("module_plan", []):
            step_num = step.get("step")
            goal = step.get("goal", "")
            modules = ", ".join(step.get("modules", []))
            why = step.get("why", "")
            router_plan_text_lines.append(
                f"- Step {step_num}: {goal} | modules: [{modules}] | why: {why}"
            )
        
        router_plan_text_lines.append("")
        router_plan_text_lines.append("Doc retrieval plan:")
        for item in plan.get("doc_retrieval_plan", []):
            module_id = item.get("module", "")
            handles = ", ".join(
                f"{h.get('kind')}:{h.get('name')}" for h in item.get("handles", [])
            )
            purpose = item.get("purpose", "")
            router_plan_text_lines.append(
                f"- Module {module_id}: {handles} | purpose: {purpose}"
            )
        
        router_plan_text = "\n".join(router_plan_text_lines)
        
        assert "EoH question type: A" in router_plan_text
        assert "Flare risk prediction" in router_plan_text
        assert "Module plan:" in router_plan_text
        assert "M1, M2" in router_plan_text
        assert "Doc retrieval plan:" in router_plan_text
        assert "pg_view:eoh_m1_patient_terrain" in router_plan_text
    
    def test_doc_plan_summary_structure(self):
        """Test the structure of doc_plan_summary for SSE emission."""
        plan = {
            "doc_retrieval_plan": [
                {
                    "module": "M1",
                    "handles": [
                        {"kind": "pg_view", "name": "eoh_m1_patient_terrain"},
                        {"kind": "pg_table", "name": "eoh_patient_stack_history"}
                    ],
                    "purpose": "Get terrain data"
                },
                {
                    "module": "M13",
                    "handles": [{"kind": "pg_view", "name": "eoh_m13_forecasts"}],
                    "purpose": "Get forecasts"
                }
            ]
        }
        
        doc_plan_summary = [
            {
                "module": item.get("module"),
                "handles": [h.get("name") for h in item.get("handles", [])],
                "purpose": item.get("purpose", ""),
            }
            for item in plan.get("doc_retrieval_plan", [])
        ]
        
        assert len(doc_plan_summary) == 2
        assert doc_plan_summary[0]["module"] == "M1"
        assert "eoh_m1_patient_terrain" in doc_plan_summary[0]["handles"]
        assert "eoh_patient_stack_history" in doc_plan_summary[0]["handles"]
        assert doc_plan_summary[1]["module"] == "M13"
        assert doc_plan_summary[1]["purpose"] == "Get forecasts"
    
    @pytest.mark.asyncio
    async def test_eoh_llm_router_called_with_patient_state(self):
        """Test that eoh_llm_router can be called with patient_state_summary."""
        mock_response = {
            "question_type": "A",
            "question_type_explanation": "Flare risk with patient context",
            "module_plan": [
                {"step": 1, "goal": "Check terrain", "modules": ["M1"], "why": "Baseline"}
            ],
            "doc_retrieval_plan": []
        }
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
        )
        
        patient_state = {
            "stack_level": 3,
            "stability_band": "unstable",
            "recent_flare": True
        }
        
        result = await eoh_llm_router(
            client=mock_client,
            question="What is this patient's flare risk?",
            patient_state_summary=patient_state
        )
        
        assert result["question_type"] == "A"
        
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        
        user_message = None
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        assert user_message is not None
        assert "stack_level" in user_message or "patient" in user_message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
