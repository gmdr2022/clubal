# CLUBAL — ROADMAP TÉCNICO

> Documento técnico sequencial.
> Define a ordem estratégica de evolução da arquitetura.
> Deve ser seguido em ordem.
> Não misturar visão de produto aqui — apenas engenharia.

---

# FASE 0 — CONTROLE E BASE

Objetivo: organizar projeto como software profissional.

- Criar repositório GitHub
- Criar .gitignore
- Criar README.md
- Criar CHANGELOG.md
- Criar VERSION
- Criar branch refactor/modularization

Tag inicial:
v0-baseline-monolith

---

# FASE 1 — BOOTSTRAP + DETECÇÃO DE AMBIENTE (CRÍTICO)

Objetivo: remover dependência direta de paths no código principal.

Criar:

core/
    bootstrap.py
    environment.py
    paths.py

environment.py:
- Detectar Windows
- Testar acesso a APPDATA
- Detectar execução portátil
- Definir MODE = "installed" | "portable"

paths.py:
- Resolver paths baseado no MODE
- Criar diretórios mínimos
- Implementar fallback silencioso
- Nunca lançar erro fatal por permissão

Resultado:
Nenhum módulo cria pasta diretamente.
Tudo passa por paths.py.

Checkpoint:
v1-bootstrap-env

---

# FASE 2 — MODULARIZAÇÃO SEM RISCO

Objetivo: separar responsabilidades sem alterar comportamento.

Estrutura alvo:

clubal/
  app.py
  clubal_main.py
  core/
  backend/
  frontend/
  assets/

Ordem segura de extração:

1. ui_theme
2. logging_manager
3. agenda_engine
4. weather_service
5. ui_header
6. ui_cards
7. ui_main
8. clubal_main vira orquestrador

Checkpoint:
v2-modular-stable

---

# FASE 3 — TELA DE BOAS-VINDAS (TV READY)

Objetivo: compatibilidade total com TV sem teclado.

Criar:

frontend/ui_screens.py

Classes:
- WelcomeScreen
- MainScreen

Regras:
- Botão grande “Iniciar”
- Auto-start configurável
- ESC visível apenas se teclado presente
- Logo animada opcional

Checkpoint:
v3-welcome-tv-ready

---

# FASE 4 — PERFORMANCE UNIVERSAL

Objetivo: rodar em PC fraco, PC moderno e TV.

Regras permanentes:

- Evitar recriar fontes
- Evitar recalcular layout desnecessário
- Cache de medições de fonte
- UI event-driven
- Weather timeout máximo 6s
- Retry máximo 2
- Sempre fallback offline
- Low_performance_mode futuro opcional

Checkpoint:
v4-performance-stable

---

# FASE 5 — CONFIG CENTRALIZADA

Criar config.json:

Campos:

- client_name
- city
- lat
- lon
- theme
- low_performance_mode
- auto_start_seconds
- portable_mode_override

Criar backend/config_manager.py:

- load_config()
- save_config()
- default_config()

Checkpoint:
v5-config

---

# FASE 6 — MIGRAÇÃO PARA JSON

Objetivo: eliminar dependência estrutural de Excel.

- Criar data/agenda.json
- Excel vira importador opcional
- Criar editor simples (modo admin oculto)

Checkpoint:
v6-no-excel

---

# FASE 7 — LICENCIAMENTO (APÓS ESTABILIDADE)

- start.exe único entrypoint
- modo demo temporário
- validação local
- futura validação online opcional

Checkpoint:
v7-licensing

---

# FASE 8 — EMPACOTAMENTO PROFISSIONAL (CRÍTICO)

Objetivo: funcionar em corporativo e TV sem dependências externas.

- Empacotar Pillow obrigatoriamente
- Garantir inclusão de graphics/**
- Resolver APP_DIR corretamente empacotado
- Compatibilidade onedir (pendrive)

Checkpoint:
v8-packaging-tv

---

# FASE 9 — ROTAÇÃO DE CONTEÚDO NA MESMA ÁREA

Objetivo: expandir conteúdo sem criar novas janelas.

Rotação:

1. AGENDA DO DIA
2. ÍNDICES CLIMÁTICOS
3. FERIADOS DO MÊS

Regras:
- Pré-instanciar frames
- Alternar visibilidade
- Não reconstruir layout
- Não criar múltiplos loops

Checkpoint:
v9-content-rotator

---

# FASE 10 — CONTENT ENGINE MODULAR

Objetivo: transformar telas em módulos plugáveis.

Criar BaseContentModule:

Atributos:
- id
- title
- priority
- refresh_interval_s

Métodos:
- build(parent)
- show()
- hide()
- refresh()

Criar ContentRegistry:

- Registrar módulos
- Ordenar por prioridade
- Controlar rotação
- Permitir ativar/desativar via config

Checkpoint:
v10-content-engine

---

# FASE 11 — PRIORIDADES + MODO EMERGÊNCIA

Sistema de prioridade:

0 = padrão  
1 = destaque  
2 = urgente  
3 = bloqueante  

Modo emergência:

Ativação por:
- data/emergency.flag
ou
- config.json

Comportamento:
- Interrompe rotação
- Pode ocupar tela inteira

Checkpoint:
v11-emergency-priority

---

# FASE 12 — WATCHDOG + AUTO-RECOVERY

Objetivo: nunca morrer por falha de módulo.

- Isolar falhas de clima
- Isolar falhas de agenda
- Fallback amigável
- Reinício controlado se erro fatal
- Safe-mode opcional

Checkpoint:
v12-watchdog-stable

---

# FASE 13 — MULTI-PROFILE / BRANDING

Estrutura:

profiles/
    default/
    cliente_x/

Cada profile contém:
- config.json
- graphics/

Seleção:
--profile=nome
ou data/profile.txt

Checkpoint:
v13-profiles

---

# FASE 14 — MODO ADMIN OCULTO

Acesso:
- Sequência de cliques
ou
- Tecla secreta

Funções:
- Editar config básico
- Importar agenda
- Limpar cache
- Ver status

Checkpoint:
v14-admin-lite

---

# FASE 15 — TELEMETRIA LOCAL LEVE

Criar stats.json:

- uptime acumulado
- últimos boots
- contagem de crashes
- último status rede

Nunca usar loop pesado.

Checkpoint:
v15-local-stats

---

# FASE 16 — ATUALIZAÇÃO OFFLINE

Estrutura:

updates/
    clubal_vX/

Se versão maior:
- sugerir atualização
- permitir rollback simples

Checkpoint:
v16-offline-update

---

# REGRAS TÉCNICAS PERMANENTES

- Iniciar em menos de 3 segundos
- Não consumir CPU constantemente
- Funcionar 100% offline
- Não depender de APPDATA
- Nunca falhar por permissão
- Troca de conteúdo apenas por troca de Frame
- Sem loops agressivos
- Tudo event-driven