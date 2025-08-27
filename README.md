# Bloqueios de Box — Yellow Self Storage

Aplicativo local em Flask para comparar relatórios de inadimplência por unidade e listar **apenas** os boxes a **Bloquear** (novos inadimplentes com `Dias Inadimplência >= 5`) e **Desbloquear** (caíram da lista) entre duas semanas.

## Como rodar

1. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv .venv
   # Windows: .venv\\Scripts\\activate
   # macOS/Linux:
   source .venv/bin/activate