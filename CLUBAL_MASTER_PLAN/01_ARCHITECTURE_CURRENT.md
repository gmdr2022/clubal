# CLUBAL — ARQUITETURA ATUAL

> Documento que descreve o estado real atual do projeto.
> Não contém futuro. Apenas como o sistema funciona hoje.

---

## 1. Stack Atual

- Linguagem: Python 3.x
- Interface: Tkinter
- Imagens: Pillow (fallback quando necessário)
- Execução: Script direto (.py)
- Empacotamento: Futuramente via PyInstaller (planejado)

O sistema foi desenvolvido com foco em leveza e compatibilidade com TVs Windows e execução portátil.

---

## 2. Estrutura Atual (Monolito em Evolução)

Estado atual do projeto:

- Arquivo principal (ex: sal.py / clubal.py)
- Lógica de agenda integrada
- Lógica de clima integrada
- UI construída diretamente no arquivo principal
- Uso parcial de cache local
- Uso opcional de Pillow para compatibilidade de PNG

A modularização está planejada, mas ainda não totalmente implementada.

---

## 3. UI — Estrutura Geral

Layout atual:

HEADER
    - Logo
    - Data
    - Relógio
    - WeatherCard

BODY
    - Duas colunas principais:
        ESQUERDA  → AGORA
        DIREITA   → PRÓXIMAS

Sistema de rotação:
    - Alternância temporizada de conteúdos
    - Uso de after() do Tkinter
    - Reaproveitamento de frames

Não há múltiplas janelas.
Não há múltiplos roots.
Tudo ocorre dentro de uma única janela principal.

---

## 4. Sistema de Agenda

- Fonte original: Excel (grade.xlsx)
- Evolução planejada: JSON (agenda.json)
- Lógica atual:
    - Filtra aulas por dia
    - Determina aulas em andamento (AGORA)
    - Determina próximas aulas (PRÓXIMAS)
    - Calcula progresso temporal
    - Atualiza UI periodicamente

Agenda depende apenas de dados locais.

---

## 5. Sistema de Clima

- API utilizada: met.no (Locationforecast)
- Uso de:
    - symbol_code
    - temperatura atual
    - previsão próxima
- Cache local:
    - weather_cache.json
- Ícones:
    - Oficiais Yr
    - Fallback via Pillow

Timeout curto e fallback offline implementado.

Se não houver internet:
    - Sistema usa último cache válido
    - Interface permanece funcional

---

## 6. Sistema de Rotação de Conteúdo

Atualmente:

- Alternância temporizada via after()
- Sem reconstrução total de layout
- Uso de pack / pack_forget
- Sistema leve

Rotação ainda não utiliza Content Engine genérico.
Funciona de forma direta na UI principal.

---

## 7. Política de Arquivos e Cache

Estado atual:

- Uso parcial de %LOCALAPPDATA%
- Criação de cache de clima
- Criação de logs simples
- Estrutura portátil ainda em evolução

Bootstrap e detecção formal de ambiente ainda não implementados completamente.

---

## 8. Pontos Técnicos Pendentes (Arquitetura)

Ainda não implementado:

- core/bootstrap.py
- core/paths.py centralizado
- core/environment.py
- Content Engine modular
- Sistema formal de prioridade
- Watchdog de recuperação
- Multi-profile

Esses itens fazem parte do ROADMAP_TECHNICAL.md.

---

## 9. Princípios Arquiteturais Atuais

- Uma única janela principal
- Nenhum loop agressivo
- Uso mínimo de threads
- Foco em estabilidade
- UI event-driven
- Cache como fallback primário

---

## 10. Limitações Atuais

- Código ainda parcialmente monolítico
- Dependência inicial de Excel
- Modularização incompleta
- Estrutura de paths ainda não totalmente centralizada
- Sistema de conteúdo ainda não baseado em engine modular

---

Este documento deve ser atualizado sempre que a arquitetura real mudar.
Não incluir ideias futuras aqui.