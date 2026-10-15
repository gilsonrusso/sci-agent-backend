from typing import Any, Dict, Optional


class StateExtractor:
    """
    Isolates the responsibility of extracting business domain structured data
    from the raw LangGraph state dictionary.

    Rule of thumb:
    - State is absolute truth.
    - Interrupt is an isolated exception (proposal before committing to state).
    """

    @classmethod
    def extract_from_state(cls, state_values: Dict[str, Any]) -> Dict[str, Any]:
        """ Extracts consolidated structured data from the resolved Graph State """
        data = {}

        def add_if_any(key, val):
            if val:
                data[key] = val

        add_if_any("suggested_articles", state_values.get("suggested_articles"))
        add_if_any("selected_articles", state_values.get("selected_articles"))
        add_if_any("roadmap", state_values.get("roadmap"))
        add_if_any("todos", state_values.get("todos"))
        add_if_any("project_title", state_values.get("project_title"))
        add_if_any("abstract", state_values.get("abstract"))
        add_if_any("project_id", state_values.get("project_id"))

        # Logical override: if selected exists, hide suggestions
        if data.get("selected_articles") and "suggested_articles" in data:
            del data["suggested_articles"]

        return data

    @classmethod
    def extract_from_interrupt(cls, interrupt_val: Any) -> Dict[str, Any]:
        """
        Extracts the PROPOSAL from the tool call.
        Handles both Middleware (action_requests) and Manual (interrupt()) formats.
        """
        data = {}

        # 1. Manual Interrupt format (dict with type)
        if isinstance(interrupt_val, dict) and interrupt_val.get("type") == "project_proposal":
            # Tenta extrair da raiz ou de um objeto aninhado 'proposta'
            val = interrupt_val
            proposta = val.get("proposta", {}) if isinstance(val.get("proposta"), dict) else val
            
            data["roadmap"] = proposta.get("tasks") or proposta.get("roadmap") or []
            data["project_title"] = proposta.get("title") or proposta.get("project_title") or ""
            data["abstract"] = proposta.get("abstract") or ""
            
            return data

        # 2. Manual Interrupt format (list of articles)
        if isinstance(interrupt_val, list):
            data["suggested_articles"] = interrupt_val
            return data

        # 3. Middleware format (action_requests)
        if isinstance(interrupt_val, dict) and "action_requests" in interrupt_val:
            for req in interrupt_val["action_requests"]:
                if req["name"] == "create_project_and_roadmap" or req["name"] == "create_project_proposal":
                    data["roadmap"] = req["args"].get("tasks", [])
                    data["project_title"] = req["args"].get("title", "")
                    data["abstract"] = req["args"].get("abstract", "")
                elif req["name"] == "present_articles_to_user_for_selection":
                    data["suggested_articles"] = req["args"].get("articles", [])
        return data

    @classmethod
    def extract_combined(
        cls, state_values: Dict[str, Any], interrupt_val: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Extracts from state and overrides with any active pending interrupt proposals.
        """
        data = cls.extract_from_state(state_values)
        if interrupt_val:
            interrupt_data = cls.extract_from_interrupt(interrupt_val)
            data.update(interrupt_data)

        return data
