"""
Ponto de entrada principal - Interface CLI interativa para o chatbot Intelbras.

Uso:
    python -m src.main
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from src.orchestrator import Orchestrator


console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           🤖  Assistente Intelbras - POC Multi-Agente        ║
║                                                              ║
║  Pergunte sobre:                                             ║
║  • Documentação técnica de produtos (configuração, specs)    ║
║  • Dados de vendas, estoque e disponibilidade                ║
║  • Informações sobre lojas e funcionários                    ║
║                                                              ║
║  Comandos: /sair  /ajuda  /modelo  /debug                    ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
**Comandos disponíveis:**
- `/sair` ou `/quit` — Encerra o chat
- `/ajuda` ou `/help` — Mostra esta mensagem
- `/modelo` — Mostra o modelo LLM em uso
- `/debug` — Alterna modo debug (mostra intent e SQL gerado)

**Exemplos de perguntas:**

*Documentação técnica (RAG):*
- Como configurar o roteador Wi-Force W6 1500?
- Qual a resolução da câmera VIP 3230 B?
- Como resetar a fechadura digital ELC 5001?
- Quais são os recursos de inteligência da VIP 3230 B?

*Dados operacionais (SQL):*
- Quantas câmeras VIP 1230 D foram vendidas?
- Qual loja vendeu mais em março?
- Qual o estoque do Wi-Force W6 1500 em São Paulo?
- Quem são os funcionários da loja de Curitiba?

*Perguntas mistas (RAG + SQL):*
- Qual câmera com WDR teve mais vendas?
- O DVR MHDX 1004-C tem estoque? E como configuro ele?
"""

EXAMPLE_QUESTIONS = [
    "Como configurar o mesh no roteador Wi-Force W6 1500?",
    "Quantas câmeras VIP 1230 D foram vendidas em janeiro?",
    "Qual o faturamento total por categoria de produto?",
    "Como funciona a detecção inteligente do DVR MHDX 1004-C?",
    "Quais lojas têm estoque da fechadura ELC 5001 RF?",
]


def show_banner():
    """Exibe o banner de boas-vindas."""
    console.print(BANNER, style="cyan")


def show_help():
    """Exibe ajuda."""
    console.print(Markdown(HELP_TEXT))


def format_intent(intent: str) -> str:
    """Formata o nome do intent para exibição."""
    labels = {
        "rag": "📚 Documentação (RAG)",
        "sql": "🗄️  Banco de Dados (SQL)",
        "both": "📚+🗄️  Ambos (RAG + SQL)",
        "general": "💬 Conversa Geral",
    }
    return labels.get(intent, f"❓ {intent}")


def main():
    """Loop principal do chat interativo."""
    show_banner()

    console.print("  Inicializando agentes...", style="dim")

    try:
        orchestrator = Orchestrator()
    except Exception as e:
        console.print(f"\n  [red]Erro ao inicializar:[/red] {e}")
        console.print("\n  Verifique:")
        console.print("  1. Arquivo .env configurado (copie de .env.example)")
        console.print("  2. API keys válidas (OPENAI_API_KEY ou ANTHROPIC_API_KEY)")
        console.print("  3. Banco SQL Server inicializado (python scripts/init_database.py)")
        console.print("  4. Base de conhecimento indexada (python -m src.rag_agent)")
        sys.exit(1)

    console.print(f"  Modelo: {orchestrator.llm.get_model_info()}", style="dim")
    console.print("  Pronto! Digite sua pergunta ou /ajuda\n", style="green")

    debug_mode = False

    while True:
        try:
            # Prompt do usuário
            user_input = console.input("[bold blue]Você:[/bold blue] ").strip()

            if not user_input:
                continue

            # Comandos especiais
            if user_input.lower() in ("/sair", "/quit", "/exit"):
                console.print("\n  Até logo! 👋\n", style="cyan")
                break

            if user_input.lower() in ("/ajuda", "/help"):
                show_help()
                continue

            if user_input.lower() in ("/modelo", "/model"):
                console.print(f"  Modelo em uso: {orchestrator.llm.get_model_info()}", style="dim")
                continue

            if user_input.lower() == "/debug":
                debug_mode = not debug_mode
                status = "ativado" if debug_mode else "desativado"
                console.print(f"  Modo debug {status}", style="yellow")
                continue

            if user_input.lower() == "/exemplos":
                console.print("\n  Exemplos de perguntas:", style="dim")
                for q in EXAMPLE_QUESTIONS:
                    console.print(f"    • {q}", style="dim")
                console.print()
                continue

            # Processa a pergunta
            console.print()
            with console.status("[bold cyan]Pensando...", spinner="dots"):
                result = orchestrator.ask(user_input)

            # Exibe debug se ativo
            if debug_mode:
                console.print(f"  [dim]Intent: {format_intent(result['intent'])}[/dim]")
                if result.get("sql_query"):
                    console.print(f"  [dim]SQL: {result['sql_query']}[/dim]")
                console.print()

            # Exibe a resposta
            intent_label = format_intent(result["intent"])
            response_text = result["response"]

            console.print(
                Panel(
                    Markdown(response_text),
                    title=f"[bold green]Assistente[/bold green] [dim]({intent_label})[/dim]",
                    border_style="green",
                    padding=(1, 2),
                )
            )
            console.print()

        except KeyboardInterrupt:
            console.print("\n\n  Interrompido. Use /sair para encerrar.\n", style="yellow")
            continue
        except Exception as e:
            console.print(f"\n  [red]Erro:[/red] {e}\n")
            if debug_mode:
                import traceback
                console.print(traceback.format_exc(), style="dim")
            continue

    # Cleanup
    orchestrator.close()


if __name__ == "__main__":
    main()
