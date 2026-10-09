# Revisão técnica — LRO Ligações 0.5.1

## Resultado e escopo

A versão foi consolidada para single plate retangular, com as premissas práticas solicitadas. **Não representa conclusão de 100% dos mecanismos possíveis das duas ligações.** A variante entre mesas está excluída; a interação da alma da viga de apoio sob tração e cortante é excluída do cálculo e identificada por uma nota simples, conforme solicitado.

## Alterações efetivas

1. Contenção da viga apoiada fixada como eficaz. Arquivos antigos são migrados para essa hipótese, mantendo esforços e dimensões. Não são considerados cortante horizontal ou momento no eixo de menor inércia; a tração axial de 2 kN permanece.
2. Soldas identificadas corretamente: chapa ao apoio, sem união soldada direta entre as duas barras.
3. Juntas internas dos perfis soldados de penetração total, com metal de adição compatível. Campo de filete de fabricação removido; verifica-se o metal-base da junta.
4. Momento local transportado até a face interna da mesa do pilar: Mma=|V|(e+tf)+|N eN|. Integração das zonas de tração e compressão; inclusão do enrugamento e revisão do escoamento localizado sob essas resultantes. A consideração de compressão localizada não transforma N em compressão axial de entrada.
5. Premissa de impedimento do deslocamento lateral relativo das mesas do pilar registrada na interface e no Word. Não é inferida da solda; a análise global do pilar é externa.
6. Variante entre mesas e enrijecedor oposto retirados da seleção e bloqueados na importação/geração de memória. Não há modelo validado suficiente para liberá-los no app.
7. Avisos distinguem dados de detalhamento de limites do modelo. Relatórios e desenhos atualizados a partir do mesmo objeto calculado.

## Reprocessamento dos arquivos enviados

| Caso | Vd / Nd de entrada | Chapa e cotas mantidas | Resultado |
|---|---|---|---|
| W360×39 → W410×38,8 | 11 / 2 kN, N tração | 160×220×7,9375 mm; a=120; g=80; z=66,5 | 23 verificações calculadas passam. Índice máximo 0,669. Interação fora do plano da alma excluída. |
| W410×38,8 → CS600×281 | 11 / 2 kN, N tração | 115×220×7,9375 mm; a=75; g=10; z=89,5 | 26 verificações calculadas passam. Índice máximo 0,454, com as premissas da versão. |

Nos dois casos, o mínimo de resultante de 45 kN governa a intensidade de cálculo: V≈44,274 kN e N≈8,050 kN. Não altera a entrada nem representa majoração de ações. O furo padrão permanece Ø20,6375 mm; desconto líquido Ø22,6375 mm quando não executado com broca.

Na ligação ao pilar, no caso mínimo, Mma≈4,312 kN·m, T≈33,565 kN e C≈25,515 kN. O termo adicional |V|tf é cerca de 0,992 kN·m. O filete de 5 mm da single plate permanece independente da premissa de penetração total do perfil.

## Por que a variante entre mesas saiu

As referências estudadas mostram participação acoplada da chapa, alma e mesas, incluindo instabilidade de um trecho comprimido e influência do detalhamento. Somar resistências de soldas isoladas ou adicionar um enrijecedor do lado oposto não demonstra a resistência nem a capacidade de rotação do conjunto. A retirada evita que verificações parciais sejam interpretadas como dimensionamento completo. Referências principais: Motallebi, Lignos e Rogers (2018), JCSR 148, 336–350; relatório SCER 005 (2014). Não há uma suposta falta genérica de PDFs a resolver: falta implementar e validar um modelo completo para essa variante.

## Limite ainda ativo na ligação viga–viga

A fórmula de linhas de plastificação confere N direto isolado, com a orientação geométrica da alma e espaço livre necessário. Ela não conclui o carregamento combinado N+V e/ou N excêntrico. A contenção da viga apoiada não resolve, por si, a deformação fora do plano da alma do apoio. Na revisão 0.5.1, esse mecanismo passa a ser uma exclusão explícita, acompanhada da nota: “Não é verificada a interação fora do plano da alma da viga de apoio sob N+V ou N excêntrico.” Quando os demais itens atendem, a conclusão é ATENDE ÀS VERIFICAÇÕES REALIZADAS. As resistências isoladas de N são omitidas nesse carregamento combinado; continuam disponíveis para N centrado sem V, dentro do domínio. Não se exige dado longitudinal para um mecanismo excluído.

Isso não pode ser chamado de aprovação total da ligação. Para fechar esse mecanismo posteriormente, é necessário método analítico com domínio compatível ou modelo numérico validado que inclua as condições do apoio e ações concomitantes. A futura ligação de cantoneiras deverá ter seu próprio caminho de forças verificado.

## Evidência de verificação

- 113 testes: equilíbrio por integração independente, exemplos de referência, casos limite, importação, hipóteses fixas, bloqueio da variante retirada e geração Word.
- 13 comparações numéricas pontuais contra referências, todas dentro das tolerâncias.
- Soluções manuais independentes: decomposição T/C sob carga linear e expressões NBR para alma do pilar, além dos testes publicados existentes.
- Dois relatórios compactos gerados pelo motor e conferidos por renderização.
- O exemplo didático W310→W150 anteriormente usado fica com índice 1,010 no novo limite conservador de escoamento localizado. Esse resultado foi preservado; não se alterou o exemplo ou o teste para forçar aprovação.

Os testes comprovam os comportamentos descritos; não equivalem a certificação ou validação integral de qualquer ligação escolhida pelo usuário.
