# LRO Ligações — versão 0.5.1

Desenvolvido por LRO Soluções de engenharia LTDA.

[LinkedIn — Lucas Oliveira](https://www.linkedin.com/in/lucas-oliveira-722723149/?isSelfProfile=true)

Single plate **retangular**, em perfis I: viga–viga e viga–mesa de pilar, encontro a 90°. Forças em kgf, momentos em kgf·m, dimensões em mm. Entradas já majoradas; não há nova majoração de ações. O mínimo resistente de 45 kN é verificado separadamente quando aplicável.

## Atualizar e abrir

1. Pare o aplicativo no terminal com **Ctrl+C**.
2. Extraia este pacote em uma **pasta nova** e preserve seus projetos JSON.
3. Abra o terminal na pasta que contém `app.py`. Ative seu ambiente Python 3.12 e execute:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Se ainda não houver ambiente: `python -m venv .venv`; no PowerShell, ative com `.venv\Scripts\Activate.ps1`. Para evitar problemas de política do PowerShell, também é possível executar diretamente `.venv\Scripts\python.exe -m pip install -r requirements.txt` e `.venv\Scripts\python.exe -m streamlit run app.py`.

A atualização é local; este pacote não altera seu app hospedado. Para hospedagem, atualize também `lro/`, `data/` e os demais arquivos do repositório, preservando a estrutura. Não envie `.venv`.

## Decisões desta versão

Na revisão 0.5.1, a interação fora do plano da alma do apoio passa de pendência para exclusão explícita, conforme solicitado. A nota não atribui resistência ao mecanismo omitido.

- **Contenção eficaz da viga apoiada é fixa**, inclusive na importação de projetos antigos. Não há pergunta na tela nem cálculo de cortante horizontal/momento no eixo de menor inércia. N axial permanece como entrada.
- A solda da ligação é **single plate → apoio**. A viga apoiada é parafusada à chapa.
- Os perfis soldados têm juntas internas mesa–alma de **penetração total, com metal de adição compatível**, por hipótese; não se informa filete de fabricação.
- Para o pilar, admite-se impedido o deslocamento lateral relativo entre as mesas na região da ligação. Essa premissa é registrada e independe da penetração total. A estabilidade global continua no projeto estrutural.
- **Chapa/enrijecedores entre mesas foram retirados**. Há aviso curto; essa variante não é avaliada nem convertida automaticamente ao abrir arquivos antigos.
- Geometrias e esforços dos dois testes enviados foram preservados. As hipóteses acima são novas e ficam expressas no JSON e no Word.

## O que os exemplos mostram

| Exemplo | Resultado | Maior índice resistente |
|---|---|---:|
| W410×38,8 → CS600×281, g=10 mm | Atende ao escopo local e às premissas declaradas | 0,454 |
| W360×39 → W410×38,8, g=80 mm | Atende às verificações realizadas; interação da alma excluída | 0,669 |

**Nota de escopo:** Não é verificada a interação fora do plano da alma da viga de apoio sob N+V ou N excêntrico. O app e o Word indicam essa exclusão junto ao resultado. O atendimento refere-se somente aos itens calculados. Os cálculos isolados de plastificação e punção sob N, e o campo de distância longitudinal, ficam restritos à tração centrada sem cortante. Outras falhas e pendências continuam sendo sinalizadas.

O perfil utilizado nos arquivos enviados é **CS 600×281**, não CVS. O catálogo ou a seção personalizada permite escolher outro perfil real; não existe equivalência automática entre essas designações.

## Arquivos e verificação

`examples/` contém os projetos atuais, desenhos SVG e duas memórias Word compactas. O arquivo `Teste_usuario_v03_original.json` mantém a entrada histórica original para conferir a migração. `docs/REVISAO_TECNICA.md` descreve a revisão; `docs/METODOLOGIA.md` contém os modelos e limites; `docs/registro_validacao.json` registra cada resultado.

**113 testes de software aprovados; 13 comparações pontuais com referências aprovadas.** Não são validação experimental integral do nó. O exemplo didático W310→W150 é mantido sem alteração e passa a ser reprovado pelo novo critério conservador de escoamento localizado no pilar (índice 1,010).

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Projetos dos esquemas 1–3 são aceitos e exportados no esquema 4, com as hipóteses fixas declaradas. Projetos da variante entre mesas são recusados. Em qualquer caso fora do domínio, o app deve ser tratado conforme o estado exibido, e não apenas pelo maior índice.
