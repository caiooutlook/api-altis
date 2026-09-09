---
type: runbook
display_name: "Configurar Acesso Remoto do DVR"
description: "Procedimento passo a passo para habilitar visualização remota dos DVRs MHDX via aplicativo e navegador"
tags: [dvr, acesso-remoto, cloud, isic, configuracao, procedimento]
lifecycle: active
verified: human-reviewed
sources:
  - uri: "https://www.intelbras.com/pt-br/suporte/dvr-acesso-remoto"
    type: documentation
    credibility:
      author: "Suporte Intelbras"
      last_modified: "2024-10-01"
---

# Configurar Acesso Remoto do DVR

## Pré-requisitos

- DVR da linha MHDX (1004-C, 3008-C, etc.) com firmware atualizado
- Conexão de internet no local do DVR (mínimo 2 Mbps de upload)
- Aplicativo Intelbras iSIC 7 instalado no celular
- Conta Intelbras Cloud (criada gratuitamente no app)

## Procedimento

### 1. Habilitar o Intelbras Cloud no DVR

1. No DVR, acesse **Menu Principal → Rede → Intelbras Cloud**
2. Marque a opção **Habilitar**
3. Verifique o campo **Status** — deve mostrar "Online"
4. Se mostrar "Offline", verifique:
   - Cabo de rede conectado à porta WAN/switch
   - DVR com IP válido (Menu → Rede → TCP/IP)
   - DNS configurado (8.8.8.8 como primário)
5. Anote ou escaneie o **QR Code** exibido na tela

### 2. Cadastrar no aplicativo iSIC 7

1. Abra o app **iSIC 7** → toque em **+** (adicionar dispositivo)
2. Selecione **Intelbras Cloud**
3. Escaneie o QR Code do DVR ou insira o número de série manualmente
4. Defina um nome para o dispositivo (ex: "Loja Centro")
5. Insira o **usuário** e **senha** do DVR
6. Toque em **Salvar**

### 3. Testar a visualização

1. Na tela inicial do app, toque no dispositivo adicionado
2. As câmeras disponíveis serão listadas
3. Toque em uma câmera para visualizar ao vivo
4. Teste a reprodução de gravações (playback)

### 4. Configurar notificações push

1. No DVR: **Menu → Eventos → Detecção de Movimento → Enviar Push** (habilitar)
2. No app: **Configurações → Notificações → Habilitar**
3. O app receberá notificações quando houver detecção de movimento

## Resolução de Problemas

| Sintoma | Ação |
|---|---|
| Cloud mostra "Offline" | Verifique internet. Teste ping para dns.google (8.8.8.8) |
| App não conecta | Atualize firmware do DVR e versão do app |
| Vídeo congela | Upload insuficiente. Reduza stream extra para D1/CIF |
| "Usuário ou senha incorretos" | Use as credenciais de acesso LOCAL do DVR (não da conta Intelbras) |
