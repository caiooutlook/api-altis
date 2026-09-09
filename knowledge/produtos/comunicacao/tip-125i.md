---
type: product
display_name: "Telefone IP TIP 125i"
description: "Telefone IP empresarial com 2 contas SIP, PoE e áudio HD"
tags: [telefone, ip, voip, sip, empresarial, poe, comunicacao]
category: Comunicação
codigo: TIP-125I
lifecycle: active
verified: human-reviewed
sources:
  - uri: "https://www.intelbras.com/pt-br/telefone-ip-tip-125i"
    type: product-page
    credibility:
      author: "Engenharia Intelbras"
      last_modified: "2024-07-10"
---

# Telefone IP TIP 125i

## Visão Geral

O TIP 125i é um telefone IP empresarial entry-level com 2 contas SIP, áudio HD (codec G.722) e alimentação PoE. Ideal para escritórios que utilizam PABX IP ou serviços de telefonia em nuvem.

## Especificações Técnicas

| Característica | Valor |
|---|---|
| Contas SIP | 2 |
| Display | LCD 132x48 pixels com backlight |
| Teclas de linha | 2 (com LEDs indicadores) |
| Áudio | HD (G.722) + banda estreita (G.711, G.729) |
| Viva-voz | Full-duplex |
| Portas de rede | 2x RJ-45 10/100 Mbps (LAN + PC) |
| PoE | 802.3af |
| Headset | Conector RJ9 |
| Agenda | Até 500 contatos |
| Registro de chamadas | 100 entradas (realizadas, recebidas, perdidas) |

## Configuração Inicial

### Conexão física

1. Conecte o cabo de rede na porta **LAN** (se PoE, alimenta automaticamente)
2. Ou use o adaptador de energia incluso (5V DC)
3. Conecte o monofone (handset) na porta RJ9 esquerda
4. Conecte headset (opcional) na porta RJ9 direita

### Obter IP

O telefone obtém IP via DHCP por padrão. Para verificar:
- Pressione **Menu → Status → Rede** — o IP será exibido no display

### Configuração via interface web

1. No computador, acesse `http://[IP-DO-TELEFONE]`
2. Login padrão: `admin` / `admin`
3. Vá em **Conta → Conta 1**
4. Configure:
   - **Ativar:** Sim
   - **Nome de exibição:** Seu ramal (ex: "Ramal 201")
   - **Servidor SIP:** IP ou domínio do PABX (ex: `192.168.1.10`)
   - **Usuário:** Número do ramal
   - **Senha:** Senha do ramal
   - **Porta:** 5060 (padrão SIP)
5. Clique em **Salvar** — o telefone registrará no PABX

## Configuração com PABX Intelbras (UnniTI/Impacta)

### Para UnniTI
1. No PABX UnniTI, crie o ramal em **Ramais → Adicionar ramal IP**
2. Anote: número, senha SIP e IP do PABX
3. No TIP 125i, configure conforme seção anterior
4. Status no display mostrará: `Ramal 201 ✓`

### Provisionamento automático
Para múltiplos telefones, use provisionamento via DHCP Option 66:
1. Configure o servidor TFTP/HTTP com os arquivos de configuração
2. No DHCP, defina Option 66 com a URL do servidor
3. Ao ligar, o telefone buscará sua configuração automaticamente

## Recursos de Áudio

- **Codec G.722 (HD Voice):** Áudio wideband com frequência até 7kHz — vozes mais naturais e inteligíveis
- **VAD (Voice Activity Detection):** Reduz uso de banda em silêncio
- **Cancelamento de eco:** AEC (Acoustic Echo Cancellation) para viva-voz
- **Ajuste de volume:** 8 níveis para monofone, viva-voz e headset independentes

## Funcionalidades de Chamada

- Transferência (cega e consultada)
- Conferência a 3
- Chamada em espera
- Rediscagem
- Não perturbe (DND)
- Desvio de chamada (incondicional, ocupado, não atende)
- Captura de chamada (pickup)
- BLF (Busy Lamp Field) — monitorar status de outros ramais

## Resolução de Problemas

| Problema | Solução |
|---|---|
| "Sem registro" no display | Verifique dados da conta SIP (servidor, usuário, senha) |
| Sem áudio na chamada | Verifique se há NAT entre telefone e PABX. Ative STUN se necessário |
| Áudio picotado | Priorize tráfego VoIP no switch/roteador (QoS/VLAN de voz) |
| PoE não funciona | Confirme que o switch suporta 802.3af e tem budget disponível |
| Reset de fábrica | Com o telefone ligado, pressione e segure OK por 10s |
