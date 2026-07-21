# ⛳ Golf Challenge — Sistema da Ativação (v2 — telão + código)

Sistema completo: **formulário no celular → código → jogo no telão → ranking**, com banco NocoDB.

## 🚨 MODO OFFLINE — AUTOMÁTICO (feito pra quem não é técnico!)

**A pessoa do estande não precisa fazer NADA se a internet cair.** O sistema se vira sozinho:

- O telão e a tela da câmera **continuam funcionando** (até apertando F5) — as telas ficam salvas no navegador na primeira vez que abrem com internet.
- Aparece o aviso **"📴 OFFLINE — salvando local"** no topo do telão. As jogadas ficam guardadas no navegador.
- O código do participante não busca do banco? A tela **já abre sozinha o campo de nome manual** — digita o nome e segue o jogo.
- Quando a internet voltar: o indicador vira **"🟢 ONLINE"** e tudo que ficou pendente **sobe sozinho** pro banco (sem apertar nada).

### Preparação (fazer UMA vez, antes do evento, por alguém do time):

1. No notebook do estande, **abrir o site com internet** (`https://proxy-golf.p9jgkb.easypanel.host/` e `/camera`) — isso "instala" as telas no navegador.
2. Carregar o **vídeo** no ⚙ Admin (fica salvo na máquina pra sempre).
3. Testar a câmera e o quadrado do buraco.
4. **Não trocar de navegador nem limpar dados de navegação** depois disso.

### Último recurso (se o notebook nunca abriu o site e não há internet nenhuma):

Dois cliques no arquivo **`INICIAR-OFFLINE-WINDOWS.bat`** (Windows) ou **`iniciar-offline-linux-mac.sh`** (Linux/Mac) dentro da pasta do projeto — o telão abre sozinho no navegador em `http://localhost:8000`. (Precisa do Python 3 instalado — deixar pronto antes do evento.)

Para subir manualmente os dados guardados no computador (opcional, um técnico faz depois): `python3 servidor.py --sync`

---

## Fluxo do evento

1. A pessoa acessa o **formulário pelo celular** (`/form`), preenche nome/WhatsApp e recebe um **código de 4 letras** na tela.
2. No estande, ela mostra o código. O staff digita no telão → **desbloqueia o jogo** (o nome vem do banco pelo código).
3. Tela fica **"Aguardando a 1ª tacada"**: cada aperto da tecla configurada (padrão **ESPAÇO**) = **1 tacada**. O **1º aperto inicia o cronômetro**.
4. A bolinha cai no buraco → a **câmera detecta e para o cronômetro sozinha** (ou o staff aperta "⛳ ACERTOU").
5. Telão vai a **tela cheia**: **HOLE-IN-ONE!** (1 tacada) ou **HOLE IN!** (2+) + "Parabéns {nome}" + confete. Depois volta pro modo dividido.
6. Jogadas detectadas pela câmera são **aprovadas automáticas**; paradas manuais caem na **Moderação** (⚙ Admin).

## Telão (LED)

- Layout: **vídeo em cima** (propaganda, arquivo local) + **jogo embaixo**.
- Tela cheia somente em: celebração (Hole in / Hole-in-One / Parabéns) e **Ranking do Dia** (botão em ⚙ Admin → "Mostrar RANKING no telão"; ESC volta).
- Vídeo: ⚙ Admin → Telão → **Carregar vídeo** — o arquivo fica salvo no navegador da máquina (IndexedDB) e **roda 100% local**, sem depender da internet.
- Dica: use **⛶ Tela cheia** (ou F11) no navegador do telão.

## Como rodar (máquina do estande)

```
python3 servidor.py
```
- Telão: http://localhost:8000  (câmera funciona por ser localhost)
- Formulário p/ celulares na mesma rede: `http://IP-DA-MÁQUINA:8000/form`
- Com o projeto **hospedado no servidor**, o formulário público é `https://seu-dominio/form`.

## Ranking

- Critério: **menos tacadas** → desempate por **menor tempo**.
- Tacadas agora são **contadas automaticamente** pelas teclas.
- Exportação CSV e backup em ⚙ Admin (PIN padrão **1234**).

## ⚙ Configurações (Admin)

- **Tecla da tacada**: clique em "tecla: … trocar" e aperte a tecla desejada (funciona com botão USB que emule teclado).
- Tempo limite, PIN, nome do evento.
- Câmera: definir o quadrado do **buraco**, sensibilidade e teste com a barra de sinal. A detecção continua ativa com o painel fechado.

## 🗄️ NocoDB (banco geral)

1. Edite `nocodb.json`: preencha `url` (ex.: `https://seu-nocodb.easypanel.host`) e `token`.
2. Rode: `python3 servidor.py --setup` → cria a base **Golf Challenge** com as tabelas:
   - **inscricoes**: Codigo, Nome, WhatsApp, Email, CriadoEm
   - **jogadas**: LocalId, Codigo, Nome, Tacadas, TempoMs, Tempo, Status, Auto, Dia, CriadoEm
3. Sem NocoDB configurado, o sistema **não para**: usa arquivos locais em `data/` (contingência).

## ☁️ Deploy no servidor (EasyPanel) — SEM GitHub

O `Dockerfile` já está pronto (python:alpine, porta 8000). Como o projeto **não vai pro GitHub**:

1. Compacte a pasta: `zip -r golf-ativacao.zip . -x "__pycache__/*" "data/*"`
2. No EasyPanel: crie o app e use a opção de **upload/imagem** (ou aponte pra um Git privado seu que não seja GitHub, ex.: Gitea do próprio servidor).
3. Configure a porta do serviço para **8000** e o domínio.
4. No servidor, o NocoDB é acessado pela `nocodb.json` (suba o arquivo já preenchido).

> Atenção: o navegador só libera a **câmera** em `localhost` ou **HTTPS**. No domínio do EasyPanel (https) funciona; rodando local funciona via localhost.
