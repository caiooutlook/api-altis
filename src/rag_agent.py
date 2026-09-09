"""
Agente RAG - Busca informações nos documentos OKF (knowledge base).

Responsável por:
- Indexar documentos OKF no ChromaDB (vector store)
- Buscar documentos relevantes para a pergunta do usuário
- Gerar respostas com base no contexto recuperado
"""

import os
from pathlib import Path
from typing import Optional

import frontmatter
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from src.config import (
    KNOWLEDGE_DIR,
    CHROMA_PERSIST_PATH,
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
)


class RAGAgent:
    """Agente de busca em documentos técnicos OKF via RAG."""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY,
        )
        self.vector_store: Optional[Chroma] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "],
        )

    def load_okf_documents(self) -> list[Document]:
        """Carrega todos os documentos .md do knowledge bundle OKF."""
        documents = []
        knowledge_path = Path(KNOWLEDGE_DIR)

        if not knowledge_path.exists():
            raise FileNotFoundError(
                f"Diretório de conhecimento não encontrado: {knowledge_path}"
            )

        for md_file in knowledge_path.rglob("*.md"):
            try:
                post = frontmatter.load(str(md_file))
                metadata = dict(post.metadata)

                # Adiciona o path relativo como identificador
                rel_path = md_file.relative_to(knowledge_path)
                metadata["source_path"] = str(rel_path)
                metadata["file_name"] = md_file.stem

                # Extrai campos OKF úteis para filtragem
                metadata["okf_type"] = metadata.get("type", "unknown")
                metadata["okf_display_name"] = metadata.get("display_name", md_file.stem)
                metadata["okf_category"] = metadata.get("category", "")
                metadata["okf_codigo"] = metadata.get("codigo", "")
                metadata["okf_lifecycle"] = metadata.get("lifecycle", "active")

                # Tags como string (ChromaDB não suporta listas em metadata)
                tags = metadata.get("tags", [])
                metadata["okf_tags"] = ", ".join(tags) if isinstance(tags, list) else str(tags)

                # Remove campos complexos que ChromaDB não suporta
                for key in ["sources", "tags"]:
                    metadata.pop(key, None)

                # O conteúdo do body é o texto principal
                content = post.content

                # Adiciona header com metadata para contexto
                header = f"Produto: {metadata.get('okf_display_name', '')}\n"
                header += f"Categoria: {metadata.get('okf_category', '')}\n"
                header += f"Código: {metadata.get('okf_codigo', '')}\n\n"

                doc = Document(
                    page_content=header + content,
                    metadata=metadata,
                )
                documents.append(doc)

            except Exception as e:
                print(f"  [WARN] Erro ao carregar {md_file}: {e}")

        return documents

    def index_documents(self, force_reindex: bool = False) -> int:
        """
        Indexa os documentos OKF no ChromaDB.
        Retorna a quantidade de chunks indexados.
        """
        persist_path = Path(CHROMA_PERSIST_PATH)

        # Se já existe e não forçou reindex, apenas carrega
        if persist_path.exists() and not force_reindex:
            self.vector_store = Chroma(
                persist_directory=CHROMA_PERSIST_PATH,
                embedding_function=self.embeddings,
                collection_name="intelbras_knowledge",
            )
            # Verifica se tem documentos
            collection = self.vector_store._collection
            if collection.count() > 0:
                return collection.count()

        # Carrega e processa documentos
        raw_docs = self.load_okf_documents()
        if not raw_docs:
            raise ValueError("Nenhum documento OKF encontrado para indexar.")

        # Faz chunking dos documentos
        chunks = self.text_splitter.split_documents(raw_docs)

        # Cria o vector store
        persist_path.mkdir(parents=True, exist_ok=True)
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=CHROMA_PERSIST_PATH,
            collection_name="intelbras_knowledge",
        )

        return len(chunks)

    def search(self, query: str, k: int = 4, filter_category: str = None) -> list[Document]:
        """
        Busca documentos relevantes para a query.

        Args:
            query: Pergunta do usuário
            k: Número de resultados
            filter_category: Filtrar por categoria OKF (opcional)

        Returns:
            Lista de Documents relevantes
        """
        if self.vector_store is None:
            self.index_documents()

        search_kwargs = {"k": k}

        if filter_category:
            search_kwargs["filter"] = {"okf_category": filter_category}

        results = self.vector_store.similarity_search(query, **search_kwargs)
        return results

    def search_with_scores(self, query: str, k: int = 4) -> list[tuple[Document, float]]:
        """Busca com scores de similaridade (menor = mais similar)."""
        if self.vector_store is None:
            self.index_documents()

        results = self.vector_store.similarity_search_with_score(query, k=k)
        return results

    def format_context(self, documents: list[Document]) -> str:
        """Formata os documentos recuperados como contexto para o LLM."""
        if not documents:
            return "Nenhum documento relevante encontrado na base de conhecimento."

        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("okf_display_name", doc.metadata.get("source_path", "?"))
            context_parts.append(
                f"--- Documento {i} (Fonte: {source}) ---\n{doc.page_content}\n"
            )

        return "\n".join(context_parts)

    def get_rag_prompt(self, query: str, context: str) -> str:
        """Monta o prompt para o LLM responder com base no contexto RAG."""
        return f"""Você é um assistente técnico especializado em produtos Intelbras.
Use APENAS as informações do contexto abaixo para responder à pergunta.
Se a informação não estiver no contexto, diga que não encontrou a informação na documentação disponível.
Sempre cite o produto/documento de onde tirou a informação.

CONTEXTO:
{context}

PERGUNTA: {query}

RESPOSTA:"""


# Script para indexação standalone
def index_knowledge_base():
    """Indexa a base de conhecimento OKF no ChromaDB."""
    print("=" * 60)
    print("  Indexando base de conhecimento OKF")
    print("=" * 60)

    agent = RAGAgent()

    print(f"\n  Diretório de conhecimento: {KNOWLEDGE_DIR}")
    print(f"  Diretório ChromaDB: {CHROMA_PERSIST_PATH}")

    docs = agent.load_okf_documents()
    print(f"\n  Documentos OKF encontrados: {len(docs)}")
    for doc in docs:
        name = doc.metadata.get("okf_display_name", "?")
        print(f"    - {name}")

    print("\n  Indexando (criando embeddings)...")
    num_chunks = agent.index_documents(force_reindex=True)
    print(f"  Chunks indexados: {num_chunks}")

    # Teste rápido de busca
    print("\n  Teste de busca: 'como configurar câmera IP'")
    results = agent.search("como configurar câmera IP", k=2)
    for r in results:
        source = r.metadata.get("okf_display_name", "?")
        print(f"    → {source}: {r.page_content[:80]}...")

    print("\n  Indexação concluída!")
    print("=" * 60)


if __name__ == "__main__":
    index_knowledge_base()
