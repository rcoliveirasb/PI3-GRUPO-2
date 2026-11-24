# 0002 - Usar Python no processamento e na API, e React + Vite na tela

Status: Aceito
Data: 2026-08-31 (API e tela definidas em 2026-10-05)

## Contexto

O núcleo do projeto é processar volumes de TC: ler arquivos MetaImage (`.mhd`/`.raw`),
converter para a escala de Hounsfield, aplicar limiares e morfologia 3D, treinar uma rede
neural e calcular estatística. Depois, a API precisava servir esses mesmos métodos, e a
tela precisava mostrar as máscaras sobre a fatia.

A equipe já conhecia Python e os notebooks Jupyter das disciplinas anteriores. O tempo
para aprender uma pilha nova era curto.

## Decisão

- **Python** (3.11 ou mais novo) para todo o processamento:
  - **SimpleITK** para ler as tomografias e as máscaras de referência;
  - **NumPy, SciPy e scikit-image** para limiar, morfologia e region growing;
  - **PyTorch** para a U-Net 2D;
  - **pandas e SciPy** para tabelas, bootstrap e teste de Wilcoxon;
  - **Jupyter** para os notebooks de cada sprint.
- **FastAPI + Uvicorn** para a API. É Python, então a API importa o mesmo código dos
  experimentos sem tradução. Gera sozinha a documentação interativa (`/docs`), e os testes
  usam o cliente de teste do próprio FastAPI com pytest.
- **React + Vite** para a tela: componentes simples, servidor de desenvolvimento rápido e
  build estático. A máscara é pintada sobre a fatia num `canvas`.

As versões exatas ficam em `requirements.txt` e `frontend/package-lock.json`.

## Consequências

**Melhora**
- Um único idioma do dado até a API: o mesmo arquivo `baseline.py` roda no notebook, no
  script de avaliação e na API.
- O ecossistema de imagem médica e de aprendizado de máquina em Python é o mais usado na
  literatura que o projeto cita, o que facilita comparar com outros trabalhos.
- A documentação da API sai pronta, e a tela consome rotas descritas por ela.

**Piora**
- Duas linguagens e dois gerenciadores de pacote (pip e npm) para instalar.
- O PyTorch é grande (centenas de MB) e às vezes não instala direto pelo `pip` no Windows; o
  README traz o comando alternativo para a versão de CPU.
- O Vite 8 exige Node.js 20.19 ou 22.12 em diante, o que pode obrigar quem vai rodar a
  atualizar o Node.
