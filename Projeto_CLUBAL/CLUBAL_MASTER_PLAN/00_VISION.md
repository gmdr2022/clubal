# CLUBAL — VISÃO E FUNDAMENTOS

## 1. Identidade do Projeto

CLUBAL (Club Agenda Live) é uma plataforma leve de comunicação institucional,
projetada para operar de forma estável em:

- PCs Windows (fracos ou modernos)
- TVs com Windows
- Execução via pendrive (modo portátil)
- Ambientes corporativos com restrições
- Ambientes offline

Stack oficial (atual):
- Python
- Tkinter
- Pillow (fallback de imagens quando necessário)

O foco é robustez, simplicidade operacional e escalabilidade progressiva.

---

## 2. Filosofia Central

CLUBAL é:

- Offline-first
- Portátil
- Leve
- Estável
- Modular
- Preparado para se tornar produto comercial

Não depende obrigatoriamente de:
- Internet
- APPDATA
- Teclado
- Instalações complexas

Sempre deve funcionar lendo apenas dados locais.

---

## 3. Pilares Técnicos Permanentes

1. Nunca falhar por ausência de permissão de escrita.
2. Sempre possuir fallback silencioso de paths.
3. Não depender rigidamente de Windows.
4. Nunca travar se não houver internet.
5. Não recriar layout inteiro em rotações.
6. Não utilizar loops agressivos.
7. Toda atualização deve ser event-driven e cacheada.
8. Build deve incluir Pillow e assets gráficos.
9. Sempre respeitar modo portátil.

---

## 4. Política de Paths (Diretriz Permanente)

Regra conceitual:

IF Windows + APPDATA acessível:
    usar %LOCALAPPDATA%\ClubAL\
ELSE:
    usar diretório local do executável:
        ./data/
        ./cache/
        ./logs/

Nunca lançar erro fatal por path.
Sempre fallback automático e silencioso.

---

## 5. Regras Fixas de Implementação (Contrato Interno)

1. Sempre indicar o que procurar com Ctrl+F.
2. Sempre indicar exatamente a ação:
   - apagar
   - colar antes
   - colar depois
   - substituir por
3. Código entregue sempre completo e pronto para copiar/colar.
4. Se houver múltiplas alterações na mesma função:
   entregar a função completa.
5. Resolver um problema por vez.
6. Evitar refatorações amplas não solicitadas.

---

## 6. Direção Estratégica

CLUBAL não é apenas uma agenda com clima.

É uma plataforma modular de comunicação institucional resiliente.

Agenda, clima, feriados e futuros módulos são conteúdos.
A estrutura é o núcleo.

Evolução deve preservar:
- Leveza
- Compatibilidade TV
- Execução portátil
- Robustez offline