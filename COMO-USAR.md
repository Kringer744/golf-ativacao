# ⛳ Golf Challenge — Sistema da Ativação (v2 — telão + código)

Sistema completo: **formulário no celular → código → jogo no telão → ranking**, com banco NocoDB.

## 🚨 PLANO B — E SE O WI-FI/4G FALHAR NO EVENTO?

O sistema roda **100% offline** no notebook do estande. Prepare ANTES do evento:

1. **Instale o Python 3** no notebook (python.org — no Windows, marque "Add to PATH").
2. **Copie a pasta do projeto** pro notebook (pendrive serve) — incluindo o arquivo `nocodb.token`.
3. **Leve o vídeo da propaganda** num pendrive.
4. Teste em casa: `python3 servidor.py` (Windows: `py servidor.py`).

**No dia, se a internet cair:**

1. No notebook: `python3 servidor.py` → abre o telão em `http://localhost:8000` (câmera funciona em localhost).
2. Carregue o vídeo (⚙ Admin → Telão) e configure a câmera normalmente — tudo funciona igual, inclusive `/camera`.
3. **Códigos**, escolha:
   - **Opção A**: hotspot local de um celular (não usa dados) → notebook conecta → os celulares dos participantes acessam `http://IP-DO-NOTEBOOK:8000/form` (o servidor mostra o IP ao iniciar). Códigos funcionam normalmente, salvos localmente.
   - **Opção B**: pula o código — o staff usa **"digitar o nome manualmente"** no telão.
4. Toda inscrição e jogada fica guardada em `data/` (arquivos JSON dentro da pasta).

**Quando a internet voltar** (no evento ou em casa):

```
python3 servidor.py --sync
```

Sobe tudo que ficou salvo localmente pro NocoDB, sem duplicar. ✅

O fallback também é **automático**: mesmo rodando na nuvem, se o NocoDB piscar, o servidor salva local, o jogo nunca trava — depois é só rodar o `--sync`.

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
