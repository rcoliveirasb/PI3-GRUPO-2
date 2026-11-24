# 0004 - Executar localmente, treinar no Colab e demonstrar com a API em modo pré-calculado

Status: Aceito
Data: 2026-11-23 (execução local definida em 2026-08-31; treino no Colab em 2026-09-14)

## Contexto

- Nenhum integrante tem GPU local. Treinar a U-Net em CPU levava horas e limitava a rede a
  poucas fatias e épocas.
- O projeto é acadêmico, sem orçamento para servidor na nuvem, e com dados de mais de 100 GB.
- A banca final é um vídeo gravado. A demonstração precisa funcionar em qualquer máquina,
  inclusive sem o HD com as tomografias.
- Mostrar números inventados na demonstração seria grave: poderiam ser confundidos com os
  resultados do artigo.

## Decisão

- **Execução local** para avaliação, KDD, API e tela, em CPU, com um ambiente virtual
  Python (`.venv`) e versões congeladas. Não há hospedagem pública.
- **Treino da U-Net no Google Colab com GPU**, pelo notebook `colab_treinar_unet.ipynb`. O
  código detecta a GPU e aumenta dados e épocas sozinho. Os pesos treinados voltam para o
  repositório.
- **A API tem três modos**, escolhidos pela variável `API_MODO`:
  - `fixo` (padrão): valores inventados, para desenvolver a tela sem dados;
  - `precalculado`: resultados reais de 3 exames, gerados pelo mesmo código do artigo e
    salvos em `pji/api/resultados_precalculados/` (316 KB). Não precisa do HD. É o modo da
    demonstração;
  - `real`: os três métodos rodando ao vivo sobre as tomografias do disco.
- A tela mostra sempre um **selo com o modo da API**.

## Consequências

**Melhora**
- Custo zero de infraestrutura.
- A U-Net passou a ser treinada com 497 exames em GPU, em vez de poucas fatias em CPU.
- A demonstração roda em qualquer computador com o repositório, e as respostas chegam em
  milissegundos.
- O selo deixa claro de onde vêm os números.

**Piora**
- Não há endereço público: quem quiser ver a tela precisa instalar e rodar localmente.
- O Colab tem sessões com tempo limitado, o que obrigou a salvar o estado do treino para
  retomar.
- O modo `precalculado` mostra só 3 exames. Para outros exames é preciso o modo `real` e as
  tomografias.
- O tempo por exame depende da máquina, e a máquina das medições não ficou registrada no
  CSV, o que enfraquece a comparação de custo entre os métodos.
