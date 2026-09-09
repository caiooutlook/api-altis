---
type: product
display_name: "DVR Multi HD MHDX 1004-C"
description: "Gravador digital de vídeo 4 canais Multi HD com detecção inteligente de movimento"
tags: [dvr, gravador, multi-hd, cftv, 4-canais, deteccao-inteligente]
category: Gravadores
codigo: MHDX-1004-C
lifecycle: active
verified: human-reviewed
sources:
  - uri: "https://www.intelbras.com/pt-br/dvr-mhdx-1004-c"
    type: product-page
    credibility:
      author: "Engenharia Intelbras"
      last_modified: "2024-12-05"
---

# DVR Multi HD MHDX 1004-C

## Visão Geral

O MHDX 1004-C é um DVR de 4 canais compatível com múltiplas tecnologias de câmeras (HDCVI, AHD, HDTVI, analógica e IP). Possui detecção inteligente de movimento que diferencia pessoas e veículos, reduzindo alarmes falsos.

## Especificações Técnicas

| Característica | Valor |
|---|---|
| Canais de vídeo | 4 BNC + 1 IP (total 5) |
| Resolução gravação | Até 1080p Lite (real-time) |
| Tecnologias suportadas | HDCVI, AHD, HDTVI, analógico, IP |
| Compressão | H.265+ / H.265 / H.264 |
| Saídas de vídeo | 1 HDMI + 1 VGA (simultâneas) |
| HD | 1x SATA (até 10TB) |
| Rede | 1x RJ-45 10/100 Mbps |
| USB | 1x USB 2.0 (frontal) + 1x USB 2.0 (traseiro) |
| Alimentação | 12V DC |
| Consumo | ≤ 10W (sem HD) |

## Detecção Inteligente de Movimento (Intelbras IA)

### O que é
Diferente da detecção de movimento convencional (baseada em pixels), a detecção inteligente usa algoritmos de deep learning para classificar o objeto em movimento:

- **Pessoa:** Dispara alarme apenas quando detecta forma humana
- **Veículo:** Dispara alarme apenas para carros, motos, caminhões

### Configuração

1. Acesse o DVR via interface web ou local
2. Vá em **Menu Principal → Eventos → Detecção Inteligente**
3. Selecione o canal desejado
4. Habilite **Detecção de Pessoa** e/ou **Detecção de Veículo**
5. Ajuste a sensibilidade (recomendado: 50-70)
6. Defina a região de detecção (máscara de área)
7. Configure as ações: gravar, alerta, e-mail, push app

### Benefícios
- Reduz até 95% dos alarmes falsos (chuva, folhas, animais)
- Busca inteligente: localize gravações por tipo de objeto
- Notificações mais relevantes no aplicativo Intelbras iSIC

## Instalação e Configuração Inicial

### Primeiro acesso

1. Conecte um monitor via HDMI ou VGA
2. Ligue o DVR — o assistente de configuração iniciará automaticamente
3. **Defina uma senha forte** (obrigatório no primeiro acesso)
4. Configure data/hora e fuso horário
5. Configure a rede (DHCP ou IP estático)
6. Adicione as câmeras (detectadas automaticamente por BNC)
7. Formate o HD em **Menu → HD → Gerenciar**

### Configuração de gravação

| Modo | Descrição | Uso de HD |
|---|---|---|
| Contínuo | Grava 24/7 | Alto |
| Por detecção | Grava apenas quando há movimento | Baixo |
| Agenda | Combina contínuo em horários e detecção em outros | Médio |

**Cálculo de armazenamento:**
- 1080p Lite, 1 câmera, 24h/dia ≈ 8GB/dia
- 4 câmeras × 30 dias ≈ 960GB (use HD de 1TB ou mais)

## Acesso Remoto

### Via aplicativo (iSIC 7)
1. No DVR, vá em **Menu → Rede → Intelbras Cloud → Habilitar**
2. No celular, instale o app **Intelbras iSIC 7** (Android/iOS)
3. Toque em **+** → **QR Code** → escaneie o QR na tela do DVR
4. Defina um nome e insira a senha do DVR

### Via navegador
1. Acesse o IP do DVR no navegador (ex: http://192.168.1.100)
2. Instale o plugin de vídeo se solicitado
3. Faça login com usuário e senha

## Resolução de Problemas

| Problema | Solução |
|---|---|
| Câmera sem imagem | Verifique se o cabo BNC está bem conectado. Teste com outro cabo. |
| HD não detectado | Desligue o DVR, verifique cabos SATA e de alimentação do HD |
| Acesso remoto falha | Verifique se o Cloud está habilitado e se há acesso à internet |
| Imagem com listras | Incompatibilidade de tecnologia. Altere em Menu → Câmera → Tipo de câmera |
