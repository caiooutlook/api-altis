"""
Agente Orquestrador - Usa LangGraph para rotear perguntas entre sub-agentes.

Fluxo:
1. Recebe a pergunta do usuário
2. Classifica a intenção (documentação técnica, dados operacionais ou ambos)
3. Roteia para o sub-agente apropriado (RAG, SQL ou ambos)
4. Consolida a resposta final
"""

from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END

from src.llm import LLMClient
from src.rag_agent import RAGAgent
from src.sql_agent import SQLAgent


# === State Definition ===

class AgentState(TypedDict):
    """Estado compartilhado entre os nós do grafo."""
    # Input
    user_query: str

    # Classificação
    intent: str  # "rag", "sql", "both", "general"

    # Resultados dos sub-agentes
    rag_context: str
    rag_response: str
    sql_query: str
    sql_results: str
    sql_response: str

    # Output final
    final_response: str


# === Orchestrator Class ===

class Orchestrator:
    """Orquestrador multi-agente com LangGraph."""

    def __init__(self):
        self.llm = LLMClient()
        self.rag_agent = RAGAgent()
        self.sql_agent = SQLAgent()
        self.graph = self._build_graph()

        # Garante que a base de conhecimento está indexada
        self.rag_agent.index_documents()

    def _build_graph(self) -> StateGraph:
        """Constrói o grafo de execução LangGraph."""
        workflow = StateGraph(AgentState)

        # Adiciona os nós
        workflow.add_node("classify", self.classify_intent)
        workflow.add_node("rag_search", self.rag_search)
        workflow.add_node("sql_search", self.sql_search)
        workflow.add_node("combine_responses", self.combine_responses)
        workflow.add_node("general_response", self.general_response)

        # Ponto de entrada
        workflow.set_entry_point("classify")

        # Roteamento condicional após classificação
        workflow.add_conditional_edges(
            "classify",
            self.route_by_intent,
            {
                "rag": "rag_search",
                "sql": "sql_search",
                "both_rag": "rag_search",
                "general": "general_response",
            },
        )

        # Após RAG, pode ir para output ou para SQL (se "both")
        workflow.add_conditional_edges(
            "rag_search",
            self.route_after_rag,
            {
                "done": END,
                "also_sql": "sql_search",
            },
        )

        # Após SQL, pode ir para output ou combinar
        workflow.add_conditional_edges(
            "sql_search",
            self.route_after_sql,
            {
                "done": END,
                "combine": "combine_responses",
            },
        )

        # Combine sempre termina
        workflow.add_edge("combine_responses", END)

        # General sempre termina
        workflow.add_edge("general_response", END)

        return workflow.compile()

    # === Nó: Classificação de Intenção ===

    def classify_intent(self, state: AgentState) -> dict:
        """Classifica a pergunta do usuário para determinar qual agente usar."""
        query = state["user_query"]

        classification_prompt = f"""Classifique a seguinte pergunta de um funcionário da Intelbras em UMA das categorias abaixo.

CATEGORIAS:
- "rag": Perguntas sobre FUNCIONAMENTO, CONFIGURAÇÃO, INSTALAÇÃO, ESPECIFICAÇÕES TÉCNICAS ou RESOLUÇÃO DE PROBLEMAS de produtos. Informações que estariam em manuais e datasheets.
- "sql": Perguntas sobre DADOS DE NEGÓCIO: vendas, faturamento, estoque, disponibilidade, funcionários, lojas, preços, quantidades vendidas. Informações que estariam em um banco de dados.
- "both": A pergunta requer AMBOS os tipos de informação (ex: "Qual câmera com WDR vendeu mais?")
- "general": Saudações, agradecimentos, ou perguntas que não se encaixam nas anteriores.

PERGUNTA: {query}

Responda APENAS com uma palavra: rag, sql, both ou general."""

        response = self.llm.complete(classification_prompt, temperature=0.0)
        intent = response.strip().lower().replace('"', "").replace("'", "")

        # Normaliza resposta
        if intent not in ("rag", "sql", "both", "general"):
            # Fallback: tenta detectar por keywords
            intent = self._keyword_fallback(query)

        return {"intent": intent}

    def _keyword_fallback(self, query: str) -> str:
        """Fallback por keywords se o LLM não classificar corretamente."""
        query_lower = query.lower()

        sql_keywords = [
            "vendeu", "vendas", "faturamento", "estoque", "quantidade",
            "loja", "lojas", "funcionário", "funcionários", "preço",
            "disponível", "disponibilidade", "quanto", "quantos",
            "top", "ranking", "mais vendido", "menos vendido",
        ]
        rag_keywords = [
            "configurar", "configuração", "instalar", "instalação",
            "funciona", "funcionamento", "como", "passo", "resolver",
            "problema", "especificação", "manual", "resetar", "firmware",
        ]

        has_sql = any(kw in query_lower for kw in sql_keywords)
        has_rag = any(kw in query_lower for kw in rag_keywords)

        if has_sql and has_rag:
            return "both"
        elif has_sql:
            return "sql"
        elif has_rag:
            return "rag"
        return "general"

    # === Roteamento ===

    def route_by_intent(self, state: AgentState) -> str:
        """Decide para qual nó ir após classificação."""
        intent = state["intent"]
        if intent == "both":
            return "both_rag"  # Começa pelo RAG, depois vai pro SQL
        return intent

    def route_after_rag(self, state: AgentState) -> str:
        """Após o RAG, decide se precisa ir para SQL."""
        if state["intent"] == "both":
            return "also_sql"
        return "done"

    def route_after_sql(self, state: AgentState) -> str:
        """Após o SQL, decide se precisa combinar com RAG."""
        if state["intent"] == "both":
            return "combine"
        return "done"

    # === Nó: Busca RAG ===

    def rag_search(self, state: AgentState) -> dict:
        """Executa busca RAG na documentação técnica."""
        query = state["user_query"]

        # Busca documentos relevantes
        documents = self.rag_agent.search(query, k=4)
        context = self.rag_agent.format_context(documents)

        # Gera resposta com base no contexto
        rag_prompt = self.rag_agent.get_rag_prompt(query, context)
        response = self.llm.complete(rag_prompt, max_tokens=1500)

        return {
            "rag_context": context,
            "rag_response": response,
            "final_response": response,
        }

    # === Nó: Busca SQL ===

    def sql_search(self, state: AgentState) -> dict:
        """Gera e executa query SQL no banco de dados."""
        query = state["user_query"]

        # Pede ao LLM para gerar a query SQL
        sql_prompt = self.sql_agent.get_sql_prompt(query)
        generated_sql = self.llm.complete(sql_prompt, temperature=0.0, max_tokens=500)

        # Limpa a query (remove possíveis ```sql ou explicações)
        generated_sql = self._clean_sql(generated_sql)

        # Executa a query
        result = self.sql_agent.execute_query(generated_sql)
        formatted_results = self.sql_agent.format_results(result)

        # Pede ao LLM para interpretar os resultados
        interpretation_prompt = self.sql_agent.get_interpretation_prompt(
            query, generated_sql, formatted_results
        )
        response = self.llm.complete(interpretation_prompt, max_tokens=1000)

        return {
            "sql_query": generated_sql,
            "sql_results": formatted_results,
            "sql_response": response,
            "final_response": response,
        }

    def _clean_sql(self, sql: str) -> str:
        """Limpa a saída do LLM para obter apenas o SQL."""
        sql = sql.strip()
        # Remove blocos de código markdown
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:])  # Remove primeira linha (```sql)
            if sql.endswith("```"):
                sql = sql[:-3]
        # Remove possível ponto final
        sql = sql.strip().rstrip(";") + ";"
        # Se tiver múltiplas linhas e a primeira for só "sql", remove
        lines = sql.split("\n")
        if lines[0].strip().lower() == "sql":
            sql = "\n".join(lines[1:])
        return sql.strip()

    # === Nó: Combinar Respostas ===

    def combine_responses(self, state: AgentState) -> dict:
        """Combina respostas do RAG e SQL em uma resposta coesa."""
        query = state["user_query"]
        rag_response = state.get("rag_response", "")
        sql_response = state.get("sql_response", "")

        combine_prompt = f"""O usuário fez uma pergunta que requer informações tanto da documentação técnica quanto dos dados de vendas/estoque.
Combine as duas respostas abaixo em uma resposta única, coesa e bem organizada em português.

PERGUNTA: {query}

INFORMAÇÃO TÉCNICA (documentação):
{rag_response}

DADOS OPERACIONAIS (banco de dados):
{sql_response}

RESPOSTA COMBINADA:"""

        response = self.llm.complete(combine_prompt, max_tokens=2000)
        return {"final_response": response}

    # === Nó: Resposta Geral ===

    def general_response(self, state: AgentState) -> dict:
        """Responde perguntas gerais / saudações."""
        query = state["user_query"]

        general_prompt = f"""Você é o assistente virtual da Intelbras, uma empresa brasileira líder em segurança eletrônica, redes e comunicação.
Responda de forma amigável e breve. Se o usuário cumprimentar, cumprimente de volta e explique o que você pode fazer:
- Responder sobre funcionamento, configuração e especificações de produtos Intelbras
- Consultar dados de vendas, estoque e disponibilidade em lojas
- Ajudar com procedimentos técnicos e resolução de problemas

MENSAGEM DO USUÁRIO: {query}

RESPOSTA:"""

        response = self.llm.complete(general_prompt, max_tokens=500)
        return {"final_response": response}

    # === Interface Pública ===

    def ask(self, question: str) -> dict:
        """
        Processa uma pergunta do usuário e retorna a resposta.

        Args:
            question: Pergunta em linguagem natural

        Returns:
            dict com: response, intent, sql_query (se aplicável), model
        """
        initial_state: AgentState = {
            "user_query": question,
            "intent": "",
            "rag_context": "",
            "rag_response": "",
            "sql_query": "",
            "sql_results": "",
            "sql_response": "",
            "final_response": "",
        }

        # Executa o grafo
        final_state = self.graph.invoke(initial_state)

        return {
            "response": final_state.get("final_response", "Desculpe, não consegui processar sua pergunta."),
            "intent": final_state.get("intent", "unknown"),
            "sql_query": final_state.get("sql_query", ""),
            "model": self.llm.get_model_info(),
        }

    def close(self):
        """Libera recursos."""
        self.sql_agent.close()
