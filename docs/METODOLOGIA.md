# Metodologia de cálculo da versão 0.5.1

## Base e unidades

NBR 8800:2024, versão corrigida 2025, prevalece sobre valores divergentes de exemplos antigos. AISC Manual 16 e Companion P901-23W e SCI P358 são complementos identificados. O catálogo de fontes está em fontes.json. Não são redistribuídos manuais de terceiros.

Internamente: N, mm e MPa; interface e resultados: kgf, kgf·m e mm. 1 kgf = 9,80665 N. Os esforços de entrada já são de cálculo. Não há majoração adicional de ações. A conferência independente do mínimo de 45 kN da NBR 6.1.5.2 mantém a direção da resultante e aparece separadamente; zero não define direção.

Uma viga, encontro a 90°, uma ou duas colunas de furos padrão alinhados, corte simples, tração axial e soldagem de oficina. Sem atrito, fadiga, ação cíclica, incêndio, compressão ou múltiplos casos.

## Geometria

- a: face de solda ao primeiro eixo de parafusos; g: face do apoio à ponta da viga; borda na viga = a − g.
- s: passo entre colunas; e = a + (ncol−1)s/2: face ao centro do grupo.
- z: topo da mesa da viga apoiada ao topo da aba parafusada, antes do recorte.
- hp = 2ev + (n−1)p; largura = a + (ncol−1)s + eh.
- N atua no eixo da viga; eN = d/2 − (z+hp/2). Inclui-se |N·eN|.
- Furos: tabela 14 da NBR; desconto líquido acrescido de 2 mm, exceto furação com broca informada.
- Distâncias às bordas e espaçamentos: 6.3.9 a 6.3.12, condição pintada/não corrosiva cadastrada. A exceção da tabela 16 usa a resistência conservadora à pressão de contato calculada.
- Folga g = 10 mm é uma sugestão de fabricação, não uma dispensa normativa. Interferências com mesas, raios, recortes, filetes e montagem continuam sendo verificadas.

## Esforços e parafusos

M = |V|e + |N·eN|. É uma envoltória de momento local; não representa uma ligação de engaste. Coordenadas do grupo em relação ao centro: J = Σ(xi²+yi²). Fxi = N/nb − M·yi/J; Fyi = V/nb + M·xi/J. O equilíbrio de forças e momento é testado.

FRd = kpega α Ab fub/γa2, com α = 0,45 ou 0,56 conforme 6.3.3.2; γa2 = 1,35. kpega = 1 − 0,01·max(0; pega−5db)/1,5, conforme 6.3.7. Não se toma a dispensa por protensão. Valores não positivos bloqueiam o cálculo.

Pressão de contato: min(1,2lc·t·fu; 2,4db·t·fu)/γa2. Adota-se o menor ligamento livre a furos ou bordas para qualquer direção de força, conservador. Não se usa automaticamente o aumento de resistência que admite grande deformação dos furos.

## Chapa e alma

Escoamento e ruptura por corte e tração: NBR 6.5, γa1 = 1,10 e γa2 = 1,35. A seção líquida vertical deduz n furos, inclusive com duas colunas: uma seção não cruza simultaneamente os dois alinhamentos horizontais.

Flexão e estabilidade da chapa: AISC F11 conforme P901 II.A-17B/19B, Cb = 1,84 e Lb = e; adota Cb = 1,0 quando existe momento adicional por N excêntrico. Mn é limitado ao momento plástico. Para duas colunas, e maior que a é mantido como opção conservadora. Ruptura por flexão: fuZn/γa2; Zn integra exatamente a seção com furos.

Interação N/V/M: AISC Manual 12-2/12-3, com resistências brasileiras explícitas. Contenção eficaz da viga apoiada é hipótese fixa solicitada pelo usuário. My=0; não há cortante horizontal nem momento no eixo de menor inércia da viga. N axial não é cortante horizontal. O momento local no plano M=|V|e+|N eN| continua integralmente considerado.

Bloco L sob V/N e U sob N: NBR 6.5.6 e interação AISC 12-1. Para o caminho completo com duas colunas, a distância até a borda inclui s, e o ramo horizontal líquido deduz 1,5 dh, contra 0,5 dh na coluna única. São avaliados também caminhos parciais por coluna. O quadro identifica caminhos completos e parciais. Furos alinhados e bordas superior/inferior da chapa simétricas; não há furos oblongos ou arranjos escalonados.

Alma apoiada: resistência local V/N, bloco U, mecanismo local de flexão/corte SCI e, quando há recorte, bloco L até cada borda livre recortada. Para duas colunas, a interação SCI da alma usa o braço até a última coluna. Soma linear de N nessa interação é uma adaptação conservadora declarada.

Alma sem recorte: instabilidade ao corte conforme NBR 5.4.3.1, kv = 5,34, sem crédito por enrijecedores transversais. λp = 1,10√(kvE/fy), λr = 1,37√(kvE/fy). Cv = 1, λp/λ ou 1,24(λp/λ)² nos respectivos intervalos. Para resistência local usa-se área h·tw, menor que d·tw.

## Ductilidade e soldas

Dispensa geométrica conforme AISC Parte 10: uma coluna requer que chapa ou alma satisfaça o limite de espessura convencional; duas colunas requerem ambas. Exige bordas horizontais de chapa e alma ≥ 2db. Fora da dispensa, calcula-se C′ = Σri[1−exp(−3,4ri/rmax)]^0,55, CIR centrado sob momento puro.

Mmax = Rn,par C′ e tmax = 6Mmax/(fy hp²). Usa-se resistência nominal brasileira com redução de pega. Não se aplica o aumento americano 1/0,90 do P901, nem o antigo 1,25: adaptação conservadora da hierarquia. A307 permanece sem validação de ductilidade para este sistema.

Dois filetes verticais: qmax = √[(N/(2h)+3M/h²)²+(V/(2h))²]. qRd = 0,6fw·w/(√2γw2), γw2 = 1,35. Sem aumento direcional de resistência. A mesma envoltória completa é usada como limite conservador na solda e no grupo.

Desenvolvimento da chapa: w ≥ max(5tp/8; √3·tp·fy/(2fw)), conforme a dedução nominal de Muir e Hewitt (2009), p.71, preservando o mínimo de detalhamento do procedimento AISC. A checagem sob esforços de cálculo continua pela NBR. Essa formulação permite calcular, por exemplo, USI-CIVIL 350 em vez de mantê-lo automaticamente como pendência.

Metal-base da chapa junto à solda: resultante por unidade de comprimento contra resistência conservadora ao corte. Nos perfis soldados, as juntas internas mesa–alma são de penetração total com metal de adição compatível, por hipótese solicitada pelo usuário. Não se pede filete interno nem se modela solda direta entre a viga e o apoio. O campo legado support_joint_weld é preservado apenas para compatibilidade e não controla a resistência. Verifica-se o metal-base da junta de penetração total, com a espessura integral da alma. A solda da single plate ao apoio continua sendo formada por dois filetes de dimensão w.

## Recortes

Seção remanescente calculada pela integração de retângulos, sem crédito pelos raios. Desconta-se a projeção dos furos na seção crítica mesmo quando ela aumenta o conservadorismo. Para uma mesa recortada, usa-se o modelo do Manual Parte 9/P901 II.A-6: f=2c/d para c≤d ou min(3;1+c/d); k=2,2(h/c)^1,65 para c≤h ou 2,2h/c; k1=max(1,61;fk); λ=h/tw; λp=0,475√(k1E/fy).

Mn=Mp se λ≤λp; Mn=Mp−(Mp−My)(λ/λp−1) se λp<λ≤2λp; Mn=0,903Ek1S/λ² se λ>2λp. Para recorte duplo com mesmo comprimento nas mesas, usa-se F11/P901 II.A-7, Cb=1,84 para V puro, ou 1,0 quando existe momento adicional de N excêntrico, Lb=c e redução líquida min(Sn/Sg; Zn/Zg).

Mc = |V|max(g+c; xúltimo) + |N|max(|d/2−yc,g|; |d/2−yc,n|). MRd=Mn/γa1. Na interação adota-se N/NRd + Mc/MRd + V/VRd ≤ 1, opção linear conservadora. Para a resistência de corte recortada adota-se kv=1,2 (modelo de seção T, NBR 5.4.3.3), também limitando conservadoramente o recorte duplo, sem contribuição da mesa na área de corte. A ruptura líquida também limita VRd. A ruptura por flexão e o bloco L são verificações adicionais.

A aplicação exige contenção lateral na raiz do recorte, c≤2d, profundidades≤d/2, h/tw≤260 e, para recorte simples, hp≥h/2. Casos fora desse domínio permanecem incompletos. O modelo de recorte não é uma análise global de viga sem travamento.

## Apoio e limites

Corte e ruptura locais do apoio são calculados. Hierarquia contra punção SCI P358 p.128: limite conservador tp≤ts fu,s/(fy,pγa2). Para V puro também se calcula tp≤ts²fu,s hp²/(6Veγa2), **sem raiz quadrada**, e aceita-se a alternativa aplicável menos restritiva. Não se estende a segunda expressão a N e V simultâneos. Ela não substitui a flexão fora do plano da alma do apoio.

Pilar: flexão local da mesa por N quando aplicável e escoamento local da alma conforme NBR 5.7. Usam-se os casos próximos à extremidade e k=tf como opções conservadoras. A chapa deve estar alinhada à alma.

### Tração direta na alma da viga de apoio

Somente para tração centrada sem cortante são calculadas duas parcelas locais: linhas de plastificação, conforme AISC Manual 16, eq.9-45 / P901 II.A-19B / Kapp (1974), e ruptura por cisalhamento perimetral. Para a plastificação, definem-se u e v como as faixas livres acima e abaixo da chapa; w = d do apoio − 2tf; L = tp. A dimensão L é paralela ao eixo da viga de apoio e não é a altura da chapa.

NRd = fy tw² [4√(2wuv(u+v)) + L(u+v)] / (4γa1uv), com γa1 = 1,10. Adotam-se bordas simplesmente apoiadas, sem crédito pelos raios nem acréscimo da dimensão carregada pela solda. A forma simétrica foi confrontada com Kapp e a forma geral com o P901. Isso confere a equação, não o comportamento completo da ligação brasileira.

O mecanismo exige espaço longitudinal de cada lado do eixo da chapa: L/2 + √[2wuv/(u+v)]. Zero no campo de distância significa não informado. Mantém-se pendência se o espaço é insuficiente; também se hp/w > 0,80, limite conservador do domínio desta implementação, não requisito da NBR. A punção isolada usa NRd = 0,6fu·2(hp+tp)tw/γa2.

A interação fora do plano sob N+V ou N excêntrico está excluída. Nesses casos, as duas resistências isoladas acima não entram no quadro de verificações nem na conclusão, e a distância longitudinal desse mecanismo não é exigida. Uma nota acompanha o resultado no app e no Word. Não se aplica ao N de serviço/cálculo comum uma resistência de amarração acidental do SCI cuja hipótese admite grandes deformações e não simultaneidade com V.

### Transmissão à alma do pilar

Mma=|V|(e+tf)+|N eN| transporta o momento até a face interna da mesa. A intensidade linear normal é p(y)=N/hp+12Mma y/hp³. Integram-se T=∫max(p,0)dy e C=∫max(−p,0)dy; T−C=N. A resultante de tração não elimina a compressão localizada causada pelo momento.

- Escoamento local: max(T,C) contra NBR 5.7.3.2(b), com k=tf e caso próximo à extremidade. Se Mma>0, adota-se ln=0: cada resultante é tratada conservadoramente como força pontual, sem ganho do comprimento da zona. Para tração uniforme sem momento, ln=hp.
- Enrugamento: C contra NBR 5.7.4.2(b), caso de extremidade e ln=0, FRd=0,33tw²√(E fy tf/tw)/γa1. Essa hipótese também evita ganhar resistência com a largura de uma distribuição não uniforme.
- Flexão local da mesa: T contra 0,5×6,25tf²fy/γa1 quando tp+2w≥0,15bf, conforme 5.7.2; quando menor, aplica-se a dispensa de 5.7.2.1.
- Metal-base na raiz da mesa: rmax=√[(N/hp+6Mma/hp²)²+(V/hp)²] contra min(0,6fy tw/γa1;0,6fu tw/γa2). Em perfil soldado, é verificação do metal-base da junta de penetração total, não dimensionamento de filete.
- Premissa explícita: deslocamento lateral relativo entre mesas do pilar impedido na região da ligação, nos termos de 5.7.5.1. É condição do projeto independente da penetração total. O app não verifica o sistema que fornece essa contenção nem a estabilidade global da barra.

A transformação de cargas e a aproximação pontual são hipóteses de implementação conservadoras, não fórmulas de uma ligação single plate específica transcritas da NBR. A resistência usa as expressões normativas identificadas. O exemplo didático W310→W150 anteriormente utilizado passa a exceder em cerca de 1% esse novo limite conservador da alma; não foi alterado para forçar aprovação.

### Variante entre mesas retirada

Não há base validada suficiente nesta implementação para a distribuição real de esforços, estabilidade acoplada, parafusos, rotação e participação do enrijecedor oposto. A variante foi retirada da seleção a pedido do usuário. Projetos antigos dessa variante são recusados com mensagem explícita; não são convertidos para chapa retangular. Rotinas geométricas históricas e integrações isoladas permanecem apenas como código/testes de componentes, sem rota de aprovação no aplicativo.

**Conclusão com exclusão:** quando todos os itens calculados atendem e não há outras pendências, o estado é ATENDE ÀS VERIFICAÇÕES REALIZADAS, acompanhado da nota de exclusão. Falhas resistentes, geometria inválida e demais pendências têm precedência. A contenção da viga apoiada não é usada como justificativa para aprovar o mecanismo omitido.
