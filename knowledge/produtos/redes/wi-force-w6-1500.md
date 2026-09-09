---
type: product
display_name: "Roteador Wi-Force W6 1500"
description: "Roteador Wi-Fi 6 AX1500 dual band com tecnologia mesh e cobertura ampliada"
tags: [roteador, wifi6, mesh, rede, dual-band, ax1500]
category: Redes
codigo: WI-FORCE-W6-1500
lifecycle: active
verified: human-reviewed
sources:
  - uri: "https://www.intelbras.com/pt-br/roteador-wi-force-w6-1500"
    type: product-page
    credibility:
      author: "Engenharia Intelbras"
      last_modified: "2024-09-30"
---

# Roteador Wi-Force W6 1500

## Visão Geral

O Wi-Force W6 1500 é um roteador Wi-Fi 6 (802.11ax) dual band com velocidade combinada de até 1500 Mbps. Suporta tecnologia mesh para ampliação de cobertura com múltiplas unidades, sem perda de velocidade no roaming.

## Especificações Técnicas

| Característica | Valor |
|---|---|
| Padrão Wi-Fi | Wi-Fi 6 (802.11ax) |
| Frequências | 2.4 GHz + 5 GHz (dual band simultâneo) |
| Velocidade 2.4 GHz | Até 300 Mbps |
| Velocidade 5 GHz | Até 1201 Mbps |
| Antenas | 4 externas omnidirecionais (5dBi) |
| Portas LAN | 3x Gigabit Ethernet |
| Porta WAN | 1x Gigabit Ethernet |
| Processador | Dual-core 1.0 GHz |
| Memória RAM | 256MB |
| Dispositivos simultâneos | Até 128 |
| Cobertura | Até 120m² (por unidade) |
| Mesh | Até 4 unidades (InMesh) |

## Recursos Wi-Fi 6

- **OFDMA (Orthogonal Frequency-Division Multiple Access):** Divide cada canal em sub-canais menores, atendendo múltiplos dispositivos simultaneamente em cada transmissão.
- **MU-MIMO 4x4:** Comunicação simultânea com até 4 dispositivos em paralelo.
- **BSS Coloring:** Reduz interferência de redes vizinhas marcando cada pacote com um "color code".
- **Target Wake Time (TWT):** Dispositivos IoT negociam horários de wake-up, economizando bateria.
- **1024-QAM:** Maior densidade de dados por símbolo, aumentando throughput em ambientes de curta distância.

## Configuração Inicial

### Via aplicativo (recomendado)

1. Conecte o cabo do provedor na porta **WAN** (azul)
2. Ligue o roteador na tomada e aguarde ~60 segundos
3. No celular, instale o app **Wi-Fi Control Intelbras** (Android/iOS)
4. Conecte ao Wi-Fi padrão: `INTELBRAS_XXXXXX` (senha na etiqueta)
5. O app detectará o roteador e iniciará o assistente
6. Configure: tipo de conexão (PPPoE/DHCP/IP fixo), nome da rede e senha
7. Pronto! O roteador reiniciará com as novas configurações

### Via navegador

1. Conecte-se ao Wi-Fi padrão ou via cabo LAN
2. Acesse `http://10.0.0.1` no navegador
3. Na primeira vez, crie uma senha de administração
4. Siga o assistente de configuração

## Configuração Mesh (InMesh)

### Adicionar nó mesh

1. Posicione o segundo roteador a no máximo 10m do principal (durante configuração)
2. No app **Wi-Fi Control**, vá em **Mesh → Adicionar dispositivo**
3. Ligue o segundo roteador e aguarde o LED piscar em azul
4. O app detectará e fará o pareamento automaticamente (~2 minutos)
5. Após pareado, mova o nó para a posição definitiva (cobertura ideal: sobreposição de 30% com o principal)

### Dicas de posicionamento mesh
- Evite paredes de concreto armado entre nós
- Altura ideal: 1,0m a 1,5m do chão
- Não coloque dentro de armários ou atrás de TVs
- Distância máxima entre nós: 12-15m em ambientes internos

## Controle Parental

1. Acesse **Configurações → Controle Parental**
2. Crie perfis por dispositivo (ex: "Tablet das crianças")
3. Defina horários de acesso (ex: bloquear 22h-7h)
4. Filtre categorias de sites (adulto, jogos, redes sociais)
5. Visualize relatórios de uso por dispositivo

## QoS (Qualidade de Serviço)

Priorize tráfego por tipo:
- **Videoconferência:** Alta prioridade para Zoom, Teams, Meet
- **Streaming:** Média prioridade para Netflix, YouTube
- **Downloads:** Baixa prioridade para torrents, atualizações

Configuração: **Menu → Rede → QoS → Habilitar** → arraste as categorias na ordem desejada.

## Resolução de Problemas

| Problema | Solução |
|---|---|
| Internet não conecta | Verifique tipo de conexão (PPPoE precisa de login/senha do provedor) |
| Wi-Fi 5 GHz não aparece | Dispositivo pode não suportar. Verifique compatibilidade |
| Velocidade baixa | Use 5 GHz para dispositivos próximos. Verifique interferência com app |
| Mesh não pareia | Faça reset no nó secundário e tente novamente a menos de 5m |
| Queda de conexão | Atualize firmware em Configurações → Sistema → Atualização |

## Atualização de Firmware

1. Acesse a interface web (`http://10.0.0.1`)
2. Vá em **Sistema → Atualização**
3. Clique em **Verificar atualização** (requer internet)
4. Se disponível, clique em **Atualizar** e aguarde (~3 minutos)
5. **Não desligue o roteador durante a atualização!**
