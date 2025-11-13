ROUTER_PROMPT = """
**INSTRUKCIJE:**
Tvoj zadatak je da na osnovu datog pitanja korisnika odlucis koji zakon ili zakoni su potrebni da bi se odgovorilo na korisnikovo pitanje.
Ponudjeni zakoni i njihova objasnjenja su sledeci:
- zakon_o_radu
 - Zakon o radu Republike Srbije reguliše radne odnose između zaposlenih i poslodavaca. Definiše prava i obaveze obe strane, uključujući radno vreme, odmore i druga odsustva i uslove za otkaz ugovora o radu. Zakon takođe obuhvata pravila vezana za ugovore o radu, minimalnu zaradu, kao i mere zaštite na radu. Osim toga, predviđa mehanizme za rešavanje radnih sporova.
- zakon_o_porezu_na_dohodak_gradjana
 - Zakon o porezu na dohodak građana reguliše način oporezivanja porezom na dohodak građana, u šta spadaju zarada, prihodi od samostalnih delatnosti, prihodi od kapitala, nepokretnosti i slično. Zakon detaljno opisuje koji sve prihodi su oporezivi ovim porezom, kao i poreske stope, osnovice, određena poreska oslobođenja i olakšice za određene kategorije građana.
- zakon_o_zastiti_podataka_o_licnosti
 - Zakon o zaštiti podataka o ličnosti štiti prava građana na privatnost njihovih ličnih podataka. Obavezuje sve organizacije koje obrađuju lične podatke da to čine transparentno, zakonito i u skladu sa definisanim svrhama. Zakon definiše prava lica na pristup, ispravku, brisanje i prenos svojih podataka o ličnosti. Takođe, ustanovljava Poverenika za informacije od javnog značaja i zaštitu podataka o ličnosti kao regulatorno telo koje nadzire primenu zakona.
- zakon_o_zastiti_potrosaca
 - Zakon o zaštiti potrošača osigurava da potrošači u Srbiji imaju prava na sigurnost i kvalitet proizvoda i usluga. Zakon propisuje obaveze trgovaca u pogledu pravilnog informisanja potrošača o proizvodima, uslugama, cenama i pravu na reklamaciju. Takođe, uključuje prava potrošača na odustanak od kupovine unutar određenog roka i prava u slučaju neispravnosti proizvoda kao i prava koja su vezana za ugovore na daljinu. 
- porodicni_zakon
 - Porodični zakon reguliše pravne odnose unutar porodice, uključujući brak, roditeljstvo, starateljstvo, hraniteljstvo i usvojenje. Zakon definiše prava i obaveze bračnih partnera, kao i prava dece i roditeljske odgovornosti. Takođe se bavi pitanjima nasleđivanja i alimentacije. 
- zakon_o_osnovama_svojinskopravnih_odnosa
 - Zakon o osnovama svojinsko-pravnih odnosa uređuje pravo svojine na pokretnim i nepokretnim stvarima, suvlasništvo, pravo službenosti (prolaz, put, uslužni prolaz), stvarne terete i zalogu. Propisuje načine sticanja, zaštite i prestanka prava svojine, uređuje komšijske odnose (međa, održavanje i uklanjanje prepreka, korišćenje zajedničkog puta), uređenje zemljišta i zaštitu poseda uključujući smetanje držaoca.
- pravne_konsultacije
 - Pravne konsultacije u vezi portala javnih nabavki sadrže odgovore na česta pitanja vezana za Portal javnih nabavki, objašnjenja procedura i pravnih aspekata javnih nabavki, kao i konsultacije o primeni Zakona o javnim nabavkama. Ovo su praktični odgovori i tumačenja koja pomažu korisnicima da razumeju kako da koriste portal i postupaju u skladu sa zakonima o javnim nabavkama.
- index
 - Sadržaj sa albaglanz.com portala (www.albaglanz.com/index.html) koji sadrži praktične odgovore i savete o javnim nabavkama, uključujući: registraciju na Portal javnih nabavki (kao naručilac i ponuđač), postupke kada ponuđač odustane, cene i greške u ponudama, ekskurzije, kontakt informacije za konsultacije (telefon i email KJN), i druge praktične situacije. **VAŽNO**: Koristi se u kombinaciji sa 'zakon_o_javnim_nabavkama' za sva pitanja o javnim nabavkama.
- paragraf_laws
 - Zakoni i propisi sa Paragraf Lex portala koji obuhvataju širok spektar pravnih oblasti uključujući krivični zakonik, carinski zakon, etičke kodekse, tarife za advokate, javne beležnike i izvršitelje, kao i različite odluke i pravilnike koji regulišu različite aspekte pravnog sistema Republike Srbije.
- carinski_zakon
 - Carinski zakon Republike Srbije koji reguliše carinske procedure, obračun i naplatu carinskih dažbina, carinske formalnosti, ovlašćenja Vlade i ministra u pogledu carinskih zakona, registraciju privrednih subjekata, i druge aspekte carinskog sistema. (Podaci se nalaze u paragraf_laws kolekciji)
- krivicni_zakonik
 - Krivični zakonik Republike Srbije koji definiše krivična dela, kazne, mere bezbednosti i vaspitne mere, kao i procedure krivičnog postupka.
- zakon_o_maloletnim_uciniocima_krivicnih_dela
 - Zakon o maloletnim učiniocima krivičnih dela i krivičnopravnoj zaštiti maloletnih lica koji reguliše posebne odredbe koje se primenjuju prema maloletnim učiniocima krivičnih dela, materijalno krivično pravo, organe koji ga primenjuju, krivični postupak i izvršenje krivičnih sankcija prema ovim učiniocima. Zakon takođe sadrži posebne odredbe o zaštiti dece i maloletnika kao oštećenih u krivičnom postupku.
- zakon_o_javnim_nabavkama
 - Zakon o javnim nabavkama koji reguliše postupke javnih nabavki, obaveze naručilaca i ponuđača, kriterije za odabir najpovoljnije ponude, i procedure sprovođenja javnih nabavki. KORISTI U KOMBINACIJI SA 'index' za pitanja o registraciji na Portalu javnih nabavki.
- ustav_republike_srbije
 - Ustav Republike Srbije koji definiše osnovne principe državnog uređenja, prava i slobode građana, organizaciju vlasti, i druge temeljne odredbe.
- zakon_o_privrednim_drustvima
 - Zakon o privrednim društvima koji reguliše osnivanje, organizaciju, upravljanje i prestanak privrednih društava.
- zakon_o_bankama
 - Zakon o bankama koji reguliše bankarske delatnosti, licenciranje banaka, nadzor nad bankarskim sistemom, i zaštitu deponenata.
- zakon_o_narodnoj_banci_srbije
 - Zakon o Narodnoj banci Srbije koji definiše ulogu, organizaciju i ovlašćenja centralne banke.
- zakon_o_porezu_na_dodatu_vrednost
 - Zakon o porezu na dodatu vrednost koji reguliše način oporezivanja PDV-om, poreske stope, osnovice, i procedure naplate.
- zakon_o_porezu_na_dobit_pravnih_lica
 - Zakon o porezu na dobit pravnih lica koji reguliše oporezivanje dobiti pravnih lica, poreske stope, osnovice, oslobođenja i olakšice.
- zakon_o_porezima_na_imovinu
 - Zakon o porezima na imovinu koji reguliše oporezivanje nepokretnosti, pokretnosti i drugih oblika imovine.
- zakon_o_porezima_na_upotrebu_drzanje_i_nosenje_dobara
 - Zakon o porezima na upotrebu, držanje i nošenje dobara koji reguliše oporezivanje određenih vrsta dobara kao što su vozila, luksuzni predmeti i slično.
- zakon_o_planiranju_i_izgradnji
 - Zakon o planiranju i izgradnji koji reguliše urbanističko planiranje, izgradnju objekata, dozvole za izgradnju i druge aspekte građevinske delatnosti.
- zakon_o_bezbednosti_i_zdravlju_na_radu
 - Zakon o bezbednosti i zdravlju na radu koji reguliše mere zaštite na radu, obaveze poslodavaca i zaposlenih, i procedure za sprečavanje povreda i oboljenja na radu.
- zakon_o_evidencijama_u_oblasti_rada
 - Zakon o evidencijama u oblasti rada koji reguliše vođenje evidencija o zaposlenima, radnom vremenu, platama i drugim aspektima radnih odnosa.
- zakon_o_izvrsenju_krivicnih_sankcija
 - Zakon o izvršenju krivičnih sankcija koji reguliše načine izvršenja kazni, mera bezbednosti i vaspitnih mera, organizaciju i rad ustanova za izvršenje kazni.
- zakon_o_javnim_agencijama
 - Zakon o javnim agencijama koji reguliše osnivanje, organizaciju, nadležnosti i rad javnih agencija.
- zakon_o_javnim_medijskim_servisima
 - Zakon o javnim medijskim servisima koji reguliše rad javnih radio i televizijskih servisa, njihovu organizaciju i finansiranje.
- zakon_o_javnim_preduzecima
 - Zakon o javnim preduzećima koji reguliše osnivanje, organizaciju, upravljanje i poslovanje javnih preduzeća.
- zakon_o_javnim_sluzbama
 - Zakon o javnim službama koji reguliše organizaciju, nadležnosti i rad javnih službi.
- zakon_o_javnim_skijalistima
 - Zakon o javnim skijalištima koji reguliše uslove, organizaciju i upravljanje javnim skijalištima, uključujući koncesije, zaštitu životne sredine i sigurnost na skijalištima. **KORISTI ZA SVA PITANJA O**: "javnim skijalištima", "skijališta", "skijanje", "koncesije za skijališta", "upravljanje skijalištima", "sigurnost na skijalištima", "zaštita životne sredine na skijalištima", "skijalište", "javno skijalište", ili bilo šta vezano za skijališta i skijanje.
- zakon_o_komorama_zdravstvenih_radnika
 - Zakon o komorama zdravstvenih radnika koji reguliše organizaciju i rad profesionalnih komora za zdravstvene radnike.
- zakon_o_mirnom_resavanju_radnih_sporova
 - Zakon o mirnom rešavanju radnih sporova koji reguliše procedure za rešavanje radnih sporova između zaposlenih i poslodavaca kroz medijaciju i druge mirne metode.
- zakon_o_naknadama_za_koriscenje_javnih_dobara
 - Zakon o naknadama za korišćenje javnih dobara koji reguliše način naplate naknada za korišćenje javnih dobara, prirodnih resursa i drugih javnih resursa.
- zakon_o_posebnim_ovlascenjima_radi_efikasne_zastite_prava_intelektualne_svojine
 - Zakon o posebnim ovlašćenjima radi efikasne zaštite prava intelektualne svojine koji reguliše mere zaštite autorskih prava, patenata, zaštitnih znakova i drugih prava intelektualne svojine.
- zakon_o_saradnji_sa_medjunarodnim_krivicnim_sudom
 - Zakon o saradnji sa Međunarodnim krivičnim sudom koji reguliše pravne odnose i proceduru saradnje sa Međunarodnim krivičnim sudom u Hagu.
- zakon_o_sedistima_i_podrucjima_sudova_i_javnih_tuzilastava
 - Zakon o sedištima i područjima sudova i javnih tužilaštava koji određuje organizaciju i teritorijalnu nadležnost sudova i tužilaštava.
- zakon_o_uslovima_izgradnje_stanova_za_pripadnike_snaga_bezbednosti
 - Zakon o uslovima izgradnje stanova za pripadnike snaga bezbednosti koji reguliše prava i uslove za sticanje stanova za pripadnike vojske, policije i drugih snaga bezbednosti.
- zakon_o_uslovima_za_upucivanje_zaposlenih_na_privremeni_rad_u_inostranstvo_i_njihovoj_zastiti
 - Zakon o uslovima za upućivanje zaposlenih na privremeni rad u inostranstvo i njihovoj zaštiti koji reguliše uslove za privremeno zapošljavanje radnika u inostranstvu i zaštitu njihovih prava.
- zakon_o_platama_u_drzavnim_organima_i_javnim_sluzbama
 - Zakon o platama u državnim organima i javnim službama koji reguliše sistem plata zaposlenih u javnom sektoru, uključujući osnovice plata, koeficijente, dodatke, nadoknade i druga primanja zaposlenih u državnim organima i javnim službama. Zakon se primenjuje na sve zaposlene u državnim organima, javnim službama, javnim agencijama i drugim javnim organizacijama.
- zakon_o_privatnom_obezbedjenju
 - Zakon o privatnom obezbeđenju koji reguliše obavezno obezbeđenje i zaštitu određenih objekata, poslove i rad pravnih i fizičkih lica u oblasti privatnog obezbeđenja, uslove za njihovo licenciranje, način vršenja poslova i ostvarivanje nadzora nad njihovim radom. Zakon obuhvata privatno obezbeđenje kroz pružanje usluga zaštite lica, imovine i poslovanja fizičkom i tehničkom zaštitom, transport novca i vrednosnih pošiljki, kao i poslove redarske službe.
- zakon_o_zastiti_korisnika_finansijskih_usluga
 - Zakon o zaštiti korisnika finansijskih usluga koji štiti prava korisnika bankarskih i drugih finansijskih usluga.
- pravilnik_o_aerosolnim_rasprasivacima
 - Pravilnik o aerosolnim raspršivačima koji reguliše tehničke zahteve, testiranje i označavanje aerosolnih raspršivača.
- pravilnik_o_areometrima
 - Pravilnik o areometrima koji reguliše tehničke zahteve, testiranje i označavanje areometara za merenje gustine tečnosti.
- zakon_o_zvanicnoj_statistici
 - Zakon o zvaničnoj statistici Republike Srbije koji reguliše organizaciju i sprovođenje statističkih istraživanja, statističke registre i zaštitu podataka.
- dinarska_vrednost_evropskih_pragova
 - Propis o dinarskoj vrednosti evropskih pragova koji određuje konverziju evropskih pragova u dinarsku vrednost za potrebe primene propisa u Srbiji.
- naredba_o_merama_postupanja_u_cilju_unistavanja_unete_alohtone_divlje_vrste_heracleum_sosnowskyi
 - Naredba o merama postupanja u cilju uništavanja unete alohtone divlje vrste Heracleum sosnowskyi koja reguliše mere za kontrolu i uništavanje ove invazivne biljne vrste. **OBAVEZNO koristi ovu naredbu za SVA pitanja koja spominju**: "Heracleum sosnowskyi", "kako uništiti ovu vrstu", "kako unistiti ovu vrstu", "uništavanje Heracleum", "alohtona vrsta", "invazivna biljka", "uništavanje biljke", "merama za uništavanje", "kontrole invazivnih biljaka", "naredba o merama postupanja", ili bilo šta vezano za uništavanje, kontrolu, ili mere za borbu protiv ove biljne vrste.
- zakon_o_regionalnom_razvoju
 - Zakon o regionalnom razvoju koji određuje nazive regiona, pokazatelje stepena razvijenosti, razvojne dokumente, subjekte regionalnog razvoja, mere i podsticaje i izvore finansiranja za sprovođenje mera regionalnog razvoja.
- zakon_o_glavnom_gradu
 - Zakon o glavnom gradu koji uređuje položaj, nadležnosti i organe grada Beograda, glavnog grada Republike Srbije. Definiše Statut grada Beograda, organizaciju i rad organa grada, nadležnosti u oblasti lokalne samouprave, i druga pitanja od važnosti za ostvarivanje prava i dužnosti grada Beograda.
- sporazum_francuska_dvostruko_oporezivanje
 - Zakon o ratifikaciji sporazuma između SFRJ i Republike Francuske o izbegavanju dvostrukog oporezivanja u oblasti poreza na dohodak koji reguliše pravila oporezivanja između Srbije i Francuske, poreski domicil, dohodak iz različitih izvora i procedure izbegavanja dvostrukog oporezivanja.
- eticki_kodeks_javnih_izvrsitelja
 - Etički kodeks javnih izvršitelja koji reguliše opšta načela i standarde profesionalnog i etičkog postupanja kojima se u radu rukovode javni izvršitelji radi jačanja njihovog profesionalizma i moralnosti. Kodeks definiše prava, obaveze i etičke standarde za javne izvršitelje i njihove zamenike, uključujući dostojnost, nezavisnost, stručnost, nepristrasnost i druge profesionalne načela.
- nema_zakona
 - Korisnikovo pitanje ne odgovara ni jednom zakonu.

**FORMAT ODGOVORA:**
- Odgovor vratiti u JSON formatu koji moze da se učita sa json.loads().
- Imena zakona mogu biti samo sledeca: zakon_o_radu, zakon_o_porezu_na_dohodak_gradjana, zakon_o_zastiti_podataka_o_licnosti, zakon_o_zastiti_potrosaca, porodicni_zakon, zakon_o_osnovama_svojinskopravnih_odnosa, pravne_konsultacije, index, paragraf_laws, carinski_zakon, krivicni_zakonik, zakon_o_maloletnim_uciniocima_krivicnih_dela, zakon_o_javnim_nabavkama, ustav_republike_srbije, zakon_o_privrednim_drustvima, zakon_o_bankama, zakon_o_narodnoj_banci_srbije, zakon_o_porezu_na_dodatu_vrednost, zakon_o_porezu_na_dobit_pravnih_lica, zakon_o_porezima_na_imovinu, zakon_o_porezima_na_upotrebu_drzanje_i_nosenje_dobara, zakon_o_planiranju_i_izgradnji, zakon_o_bezbednosti_i_zdravlju_na_radu, zakon_o_evidencijama_u_oblasti_rada, zakon_o_izvrsenju_krivicnih_sankcija, zakon_o_javnim_agencijama, zakon_o_javnim_medijskim_servisima, zakon_o_javnim_preduzecima, zakon_o_javnim_sluzbama, zakon_o_javnim_skijalistima, zakon_o_komorama_zdravstvenih_radnika, zakon_o_mirnom_resavanju_radnih_sporova, zakon_o_naknadama_za_koriscenje_javnih_dobara, zakon_o_posebnim_ovlascenjima_radi_efikasne_zastite_prava_intelektualne_svojine, zakon_o_saradnji_sa_medjunarodnim_krivicnim_sudom, zakon_o_sedistima_i_podrucjima_sudova_i_javnih_tuzilastava, zakon_o_uslovima_izgradnje_stanova_za_pripadnike_snaga_bezbednosti, zakon_o_uslovima_za_upucivanje_zaposlenih_na_privremeni_rad_u_inostranstvo_i_njihovoj_zastiti, zakon_o_platama_u_drzavnim_organima_i_javnim_sluzbama, zakon_o_privatnom_obezbedjenju, zakon_o_zastiti_korisnika_finansijskih_usluga, pravilnik_o_aerosolnim_rasprasivacima, pravilnik_o_areometrima, zakon_o_zvanicnoj_statistici, dinarska_vrednost_evropskih_pragova, naredba_o_merama_postupanja_u_cilju_unistavanja_unete_alohtone_divlje_vrste_heracleum_sosnowskyi, zakon_o_regionalnom_razvoju, zakon_o_glavnom_gradu, sporazum_francuska_dvostruko_oporezivanje, eticki_kodeks_javnih_izvrsitelja, nema_zakona.
- Jedno pitanje korisnika moze da se odnosi na vise zakona.
- Vrati zakone koji mogu da pomognu prilikom generisanja odgovora.
- ZA PITANJA O JAVNIM NABAVKAMA, REGISTRACIJI NA PORTALU, CENAMA, PONUDAMA I DRUGIM PRAKTIČNIM PITANJIMA: UVEK vrati i 'zakon_o_javnim_nabavkama' i 'index' (albaglanz.com/index.html) da bi chatbot mogao da citira i zakonske odredbe i praktične savete. 'index' kolekcija sadrži praktične odgovore i savete koje je važno uključiti.
- PRIOITET ZA 'index' KOLEKCIJU: Za sva pitanja koja se tiču javnih nabavki, registracije, postupaka, cena, ponuda, i drugih praktičnih aspekata javnih nabavki, OBAVEZNO uključi 'index' kolekciju zajedno sa relevantnim zakonima.
- OBAVEZNO ZA HERACLEUM SOSNOWSKYI: Za BILO KOJE pitanje koje spominje "kako uništiti", "kako unistiti", "uništavanje biljke", "alohtona vrsta", "invazivna biljka", "Heracleum", ili bilo šta vezano za uništavanje ili kontrolu biljaka, OBAVEZNO vrati 'naredba_o_merama_postupanja_u_cilju_unistavanja_unete_alohtone_divlje_vrste_heracleum_sosnowskyi'. Ne vracaj "nema_zakona" za ova pitanja.
- OBAVEZNO ZA PITANJA O PRAVU PROLAZA/SLUŽBENOSTI: Za sva pitanja u kojima se spominju "komšija", "put kroz moje zemljište", "pravo prolaza", "službenost", "put preko tuđe parcele", "ometanje poseda", "međa", "ograda", "putni prolaz", "traktor prelazi", ili druge situacije oko korišćenja ili zaštite zemljišta između suseda, OBAVEZNO vrati 'zakon_o_osnovama_svojinskopravnih_odnosa'. Ne vraćaj "nema_zakona" za ova pitanja.
- OBAVEZNO ZA JAVNA SKIJALIŠTA: Za BILO KOJE pitanje koje spominje "javnim skijalištima", "skijališta", "skijanje", "koncesije za skijališta", "upravljanje skijalištima", "sigurnost na skijalištima", "zaštita životne sredine na skijalištima", "skijalište", "javno skijalište", "ski-staza", "ski-poligon", "ski-ruta", ili bilo šta vezano za skijališta i skijanje, OBAVEZNO vrati 'zakon_o_javnim_skijalistima'. Ne vracaj "nema_zakona" za ova pitanja.
- Ukoliko korisnikovo pitanje ne odgovara ni jednom zakonu vrati listu sa generickim stringom: ["nema_zakona"].

**PRIMER ODGOVORA:**
{{
    response: ["ime_zakona"]
}}
"""

USER_QUERY = """
**PITANJE KORISINKA:**
{query}
"""

ROUTER_PROMPT_ENG = """
Your task is to decide which law or laws are needed to answer the user's question based on the given question.
The provided laws and their explanations are as follows:
- labor_law
 - The Labor Law of the Republic of Serbia regulates labor relations between employees and employers. It defines the rights and obligations of both parties, including working hours, leaves, and conditions for termination of employment contracts. The law also covers rules related to employment contracts, minimum wage, and workplace safety measures. Additionally, it provides mechanisms for resolving labor disputes.
- personal_income_tax_law
 - The Personal Income Tax Law regulates the taxation of citizens' income, including salaries, self-employment income, capital income, real estate income, and more. The law details which incomes are taxable, as well as tax rates, bases, certain tax exemptions, and reliefs for specific categories of citizens.
- personal_data_protection_law
 - The Personal Data Protection Law protects citizens' rights to the privacy of their personal data. It obligates all organizations processing personal data to do so transparently, legally, and in accordance with defined purposes. The law defines the rights of individuals to access, correct, delete, and transfer their personal data. It also establishes the Commissioner for Information of Public Importance and Personal Data Protection as the regulatory body overseeing the law's implementation.
- consumer_protection_law
 - The Consumer Protection Law ensures that consumers in Serbia have rights to the safety and quality of products and services. The law prescribes the obligations of traders regarding the proper information of consumers about products, services, prices, and the right to file complaints. It also includes consumers' rights to withdraw from a purchase within a specified period and rights in case of defective products as well as rights related to distance contracts.
- family_law
 - The Family Law regulates legal relations within the family, including marriage, parenthood, guardianship, foster care, and adoption. The law defines the rights and obligations of spouses, as well as children's rights and parental responsibilities. It also addresses issues of inheritance and alimony.
- legal_consultations
 - Legal consultations regarding the public procurement portal contain answers to frequently asked questions about the Public Procurement Portal, explanations of procedures and legal aspects of public procurement, and consultations on the application of the Law on Public Procurement. These are practical answers and interpretations that help users understand how to use the portal and act in accordance with public procurement laws.
- no_law
 - The user's question does not correspond to any law.

**RESPONSE FORMAT:**
- Return the response in JSON format that can be loaded with json.loads().
- The names of the laws can only be the following: labor_law, personal_income_tax_law, personal_data_protection_law, consumer_protection_law, family_law, legal_consultations, no_law.
- A user's question can relate to multiple laws.
- Return the laws that can help in generating the answer.
- If the user's question does not correspond to any law, return a list with the generic string: ["no_law"].
- Example JSON response:

{{
    "response": ["law_name"]
}}

**USER'S QUESTION:**
{query}
"""


DEFAULT_ROUTER_RESPONSE = "nema_zakona"
