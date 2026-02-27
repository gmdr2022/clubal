# CLUBAL — CHANGELOG

Este documento registra mudanças reais do projeto.
Apenas fatos implementados.
Não incluir planos futuros aqui.

Formato de versão:

vMAJOR.MINOR.PATCH
ou
vX-tag-descritiva (enquanto ainda não há versionamento semântico formal)

---

# v0-baseline-monolith
Data: 2026-02-XX

Estado inicial documentado.

- Aplicação funcional em arquivo monolítico
- Agenda baseada em Excel (grade.xlsx)
- Weather integrado com met.no
- Cache local de clima
- Uso opcional de Pillow para compatibilidade de PNG
- Sistema de rotação implementado via Tkinter after()
- Interface única (single root)
- Compatibilidade básica com TV
- Execução direta via script Python

---

# v1-documentation-structure
Data: 2026-02-XX

Criação da estrutura de planejamento e arquitetura.

Adicionado:

- Pasta CLUBAL_MASTER_PLAN/
- 00_VISION.md
- 01_ARCHITECTURE_CURRENT.md
- 02_ROADMAP_TECHNICAL.md
- 03_ROADMAP_PRODUCT.md
- 04_EXECUTIVE_SUMMARY.md
- Estrutura inicial formal de versionamento

Nenhuma alteração funcional no código.
Apenas estrutura organizacional.

---

# Próximas versões (quando implementadas)

Exemplo de padrão:

# v1-bootstrap-env
- Implementado core/bootstrap.py
- Implementado environment.py
- Implementado paths.py
- Centralização completa de criação de diretórios
- Fallback portátil validado

# v2-modular-stable
- Separação de agenda_engine
- Separação de weather_service
- Criação de frontend/
- Código principal convertido em orquestrador

---

Regras para manter este documento:

1. Registrar apenas o que foi realmente implementado.
2. Não registrar ideias.
3. Cada versão deve conter:
   - Data
   - Lista objetiva de mudanças
4. Nunca remover histórico anterior.