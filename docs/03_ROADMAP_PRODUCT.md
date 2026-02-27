# CLUBAL — ROADMAP DE PRODUTO

> Documento estratégico.
> Define a evolução funcional e posicionamento do CLUBAL como produto.
> Não contém detalhes de implementação técnica profunda.
> Foco: valor, diferenciação e escalabilidade.

---

# 1. POSICIONAMENTO

CLUBAL deixa de ser apenas “agenda com clima”.

Passa a ser:

> Plataforma Modular de Comunicação Institucional Leve

Agenda, clima e feriados são módulos.
A estrutura é o núcleo.

O produto deve ser:

- Estável
- Portátil
- Offline-first
- Compatível com TV
- Comercializável

---

# 2. NÚCLEO DE CONTEÚDO MODULAR

Todos os conteúdos são tratados como módulos.

Exemplos atuais:
- Agenda do Dia
- Índices Climáticos
- Calendário de Feriados

Exemplos futuros possíveis:
- Avisos institucionais
- Campanhas internas
- Eventos especiais
- Mensagens patrocinadas
- Comunicados urgentes
- QR Code dinâmico
- Ranking interno

Adicionar módulo não deve exigir alterar arquitetura base.

---

# 3. SISTEMA DE PRIORIDADE

Cada módulo pode possuir prioridade:

0 = padrão  
1 = destaque  
2 = urgente  
3 = bloqueante  

Exemplo de comportamento:

- Aviso urgente interrompe rotação.
- Emergência ocupa tela inteira.
- Destaque aparece com maior frequência.

Isso transforma o CLUBAL em ferramenta institucional real.

---

# 4. MODO EMERGÊNCIA

Objetivo: uso institucional crítico.

Ativação simples:
- Arquivo local
- Campo no config

Comportamento:
- Interrompe rotação
- Pode ocupar tela principal
- Compatível com modo offline

Diferencial estratégico para escolas, clubes, instituições.

---

# 5. MULTI-CLIENTE / BRANDING

Objetivo: transformar em produto vendável.

Estrutura por profile:

- Logo do cliente
- Cores
- Cidade
- Configurações
- Feriados locais

Um único build deve atender múltiplos clientes.

---

# 6. EXPERIÊNCIA VISUAL EVOLUTIVA

Sem perder leveza:

- Transições suaves
- Ajuste automático de contraste
- Layout proporcional (não fixo por resolução)
- Microanimações discretas
- Modo noturno real automático

Tudo respeitando:
- Performance
- Portabilidade
- TV compatibility

---

# 7. MODO ADMINISTRATIVO

Acesso oculto.

Funções mínimas:
- Alterar configurações
- Importar agenda
- Limpar cache
- Ver status do sistema
- Ativar modo emergência

Sem complexidade.
Sem painel web.
Tudo local.

---

# 8. TELEMETRIA LOCAL

Sem servidor externo.

Registrar:
- Tempo ativo
- Últimos reinícios
- Falhas
- Status de rede

Auxilia suporte técnico e profissionalização.

---

# 9. EVOLUÇÃO COMERCIAL FUTURA

Após estabilidade técnica:

- Licenciamento local
- Modo demo
- Atualização offline
- Futuro auto-update opcional
- Pacotes por cliente

CLUBAL deve ser:
- Simples para instalar
- Simples para operar
- Difícil de quebrar

---

# 10. DIREÇÃO DE LONGO PRAZO

CLUBAL não é apenas software.
É uma base de produto escalável.

Evolução deve sempre preservar:

- Leveza
- Execução portátil
- Independência de internet
- Robustez offline
- Estrutura modular
- Compatibilidade com TV

Produto cresce.
Complexidade não.