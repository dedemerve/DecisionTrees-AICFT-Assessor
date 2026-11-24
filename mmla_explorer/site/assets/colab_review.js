/* Colab scoring human-validation review interface */
(function (root) {
  'use strict';

  var STORAGE_KEY = 'colabReview_v1';
  var CRIT_IDX_KEY = 'colabReview_critIdx_v1';

  var CRIT_ORDER = ['S1.3','S1.4','S2.2','S3.1','S3.2','S3.3','S6.1','S6.2','S6.3','S6.4','S7.2','S7.3'];

  var Q_CODE = {
    'S1.3':'Q1','S1.4':'Q2','S2.2':'Q3',
    'S3.1':'Q4','S3.2':'Q5','S3.3':'Q6',
    'S6.1':'Q7','S6.2':'Q8','S6.3':'Q9','S6.4':'Q10',
    'S7.2':'Q11','S7.3':'Q12'
  };

  /* ---- persistence ---- */
  function load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch (e) { return {}; }
  }
  function save(ratings) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(ratings)); } catch (e) {}
  }
  function loadCritIdx() {
    try { return parseInt(localStorage.getItem(CRIT_IDX_KEY) || '0', 10) || 0; }
    catch (e) { return 0; }
  }
  function saveCritIdx(idx) {
    try { localStorage.setItem(CRIT_IDX_KEY, String(idx)); } catch (e) {}
  }

  /* ---- criterion labels (Turkish) ---- */
  var TR_LABELS = {
    'S1.3': 'VKA: Habitat dengesizliğinin etkisi (3p)',
    'S1.4': 'VKA: Türlere göre vücut kütlesi karşılaştırması (3p)',
    'S2.2': 'Araştırma sorusu kalitesi (2p)',
    'S3.1': 'Bölme parametreleri: stratify + test_size (2p)',
    'S3.2': 'Stratify kaldırmanın kavramsal etkisi (2p)',
    'S3.3': 'Rastgelelik ve yeniden üretilebilirlik (2p)',
    'S6.1': 'Yansıma S6.1: En önemli öğrenme (5p)',
    'S6.2': 'Yansıma S6.2: Veri anlayışı (5p)',
    'S6.3': 'Yansıma S6.3: Model performansı (5p)',
    'S6.4': 'Yansıma S6.4: Sınırlamalar ve alternatifler (5p)',
    'S7.2': 'Çapraz karşılaştırma: örüntü akıl yürütme (4p)',
    'S7.3': 'Çapraz karşılaştırma: Fasıl tartışması (4p)'
  };

  /* ---- question prompts shown to students (Turkish) ---- */
  var TR_QUESTIONS = {
    'S1.3': 'Habitat sınıflarındaki dengesizlik (Yer çok, Ağaç az) modelin tahminlerini nasıl etkiler? Hangi sınıf daha iyi tahmin edilir, neden?',
    'S1.4': 'Türlere göre vücut kütlesi dağılımına baktığında hangi tür en ağır, hangi tür en hafif? Biyolojik bir açıklama yapabilir misin?',
    'S2.2': 'Bu veri setiyle test etmek istediğin araştırma sorularını yaz. Her hedef değişken (YaşamAlanı, Tür, Cinsiyet) için ayrı bir araştırma sorusu oluştur.',
    'S3.1': 'train_test_split fonksiyonunda test_size, stratify ve random_state parametrelerini nasıl ayarladın? (Beklenen: test_size=0.2, stratify=y, random_state=42)',
    'S3.2': 'Eğer stratify parametresini kaldırırsan ne olur? Sınıf dağılımı üzerindeki etkisini açıkla.',
    'S3.3': 'random_state parametresini değiştirirsen sonuçlar nasıl değişir? Bu parametrenin rolü nedir?',
    'S6.1': 'Soru 1 — Bu ödevde veri kartları, CODAP ve Python olmak üzere üç farklı ortamda çalıştın. Her birinde ne öğrendiğini ve hangi hataları fark ettiğini açıkla.',
    'S6.2': 'Soru 2 — Karar ağacının kök düğümünde hangi özellik yer aldı? Bu seni şaşırttı mı? Hangi habitat sınıfı en zor sınıflandırıldı ve neden?',
    'S6.3': 'Soru 3 — Modelinin yanlış sınıflandırma oranı (MCR) neydi? En iyi ve en kötü tahmin edilen sınıf hangisiydi? İdeal bir MCR eşiği ne olmalıdır?',
    'S6.4': 'Soru 4 — Modelindeki sistematik hata örüntüsünü açıkla. Modeli iyileştirmek için ne yapardın? Karar ağacına alternatif hangi modeli kullanırdın ve neden?',
    'S7.2': 'Üç hedef değişken (YaşamAlanı, Tür, Cinsiyet) için en iyi derinlik değerleri farklı mıydı? Neden farklı olduğunu MCR değerlerine veya veri özelliklerine dayanarak açıkla.',
    'S7.3': 'Farklı hedef değişkenler için karar ağacının kök düğümü değişti mi? Bu değişimin biyolojik veya istatistiksel bir açıklaması var mı?'
  };

  /* ---- rubric criteria per score level ---- */
  var TR_RUBRICS = {
    'S1.3': [
      { score: 3, text: 'Çoğunluk sınıfının (Yer) daha iyi tahmin edileceğini, azınlık sınıfının (Ağaç) daha fazla hata alacağını model düzeyinde açıklar — yanlılık, duyarlılık veya sınıf ağırlığı gibi kavramlarla.' },
      { score: 2, text: 'Doğru yönü kısa bir açıklamayla belirtir; mekanizma tam değil.' },
      { score: 1, text: 'Belirsiz — mekanizma olmadan "dengesizlik kötüdür" gibi genel bir ifade.' },
      { score: 0, text: 'Yanıt yok veya yanlış yön.' }
    ],
    'S1.4': [
      { score: 3, text: 'Sceloporus\'u en ağır, Uta\'yı en hafif olarak doğru sıralar VE biyolojik ya da morfolojik bir neden verir.' },
      { score: 2, text: 'Doğru sıralama ama açıklama yok — ya da açıklama var ama sıralama yanlış.' },
      { score: 1, text: 'Kısmi veya belirsiz.' },
      { score: 0, text: 'Yanıt yok.' }
    ],
    'S2.2': [
      { score: 2, text: 'Tüm sorular hedef değişkeni ve tahmin amacını içerecek şekilde test edilebilir araştırma soruları olarak çerçevelenmiş.' },
      { score: 1, text: 'Sorular var ama belirsiz ya da hipotez biçiminde çerçevelenmemiş.' },
      { score: 0, text: 'Hepsi null veya sadece değişken adları kopyalanmış.' }
    ],
    'S3.1': [
      { score: 2, text: 'test_size=0.2 VE stratify kullanılmış VE random_state belirtilmiş.' },
      { score: 1, text: 'test_size ve stratify doğru ama random_state yok.' },
      { score: 0, text: 'stratify kullanılmamış VEYA test_size yanlış.' }
    ],
    'S3.2': [
      { score: 2, text: 'stratify\'ı kaldırmanın sınıf dağılımı dengesini bozacağını açıklar — test setinde azınlık sınıfları (Ağaç) yetersiz temsil edilebilir, değerlendirme zarar görür.' },
      { score: 1, text: 'Denge veya adalet kavramından söz eder ama spesifik sonuç yok.' },
      { score: 0, text: 'Yanıt yok veya yanlış yön.' }
    ],
    'S3.3': [
      { score: 2, text: 'random_state\'in karıştırma tohumunu (seed) kontrol ettiğini açıklar VE tekrarlanabilirlik kavramını belirtir — aynı değerle kodu her çalıştırdığında aynı bölünme elde edilir.' },
      { score: 1, text: 'Sonuçların/bölmenin değişeceğini söyler ve random_state\'in bölmeyi kontrol ettiğini belirtir; ama tekrarlanabilirlik (reproducibility) kavramı eksik.' },
      { score: 0, text: 'Yanıt yok veya yalnızca "sonuçlar değişir" düzeyinde.' }
    ],
    'S6.1': [
      { score: 5, text: 'Üç ortamın (veri kartları, CODAP, Python) her biri için ayrı ve özlü gözlemler yapar; hata tespitini de ele alır.' },
      { score: 4, text: 'Üç ortam var ama birinde gözlem yüzeysel.' },
      { score: 3, text: 'İki ortam ele alınmış ya da hata tespiti eksik.' },
      { score: 2, text: 'Bir ortam veya çok genel ifadeler.' },
      { score: 1, text: 'Çok belirsiz.' },
      { score: 0, text: 'Yanıt yok.' }
    ],
    'S6.2': [
      { score: 5, text: 'Kök düğüm özelliğinin biyolojik açıklaması, beklenti/sürpriz tartışması VE hangi habitatın en zor sınıflandırıldığına dair biyolojik neden — üçü de var.' },
      { score: 4, text: 'Bu üç boyuttan ikisi.' },
      { score: 3, text: 'Bir boyut veya kısmi.' },
      { score: 2, text: 'Çok genel.' },
      { score: 1, text: 'Çok belirsiz.' },
      { score: 0, text: 'Yanıt yok.' }
    ],
    'S6.3': [
      { score: 5, text: 'Doğru MCR değeri (en az bir hedef için gerçek değere ±0.01), en iyi ve en kötü tahmin edilen sınıfı nedeniyle belirtir, ideal eşik önerir, hedefler arası karşılaştırma yapar.' },
      { score: 4, text: 'Dört bileşenden üçü.' },
      { score: 3, text: 'İkisi.' },
      { score: 2, text: 'Biri.' },
      { score: 1, text: 'Çok belirsiz.' },
      { score: 0, text: 'Yanıt yok.' }
    ],
    'S6.4': [
      { score: 5, text: 'Sistematik hata örüntüsü, veri/model iyileştirme önerisi, alternatif model ve nedeni, aşırı öğrenme sınırlamasını içeren sade açıklama — dördü de var.' },
      { score: 4, text: 'Dört bileşenden üçü.' },
      { score: 3, text: 'İkisi.' },
      { score: 2, text: 'Biri.' },
      { score: 1, text: 'Çok belirsiz.' },
      { score: 0, text: 'Yanıt yok.' }
    ],
    'S7.2': [
      { score: 4, text: 'En iyi derinliklerin neden farklı olduğunu açıklar — birden fazla hedef için spesifik MCR değerleri ya da derinlik numaraları verir, veri odaklı veya biyolojik neden sunar.' },
      { score: 3, text: 'Derinliklerin farklı olduğunu söyler, kısmi neden verir.' },
      { score: 2, text: 'Farklı olduğunu söyler ama neden yok.' },
      { score: 1, text: 'Belirsiz.' },
      { score: 0, text: 'Yanıt yok veya karşılaştırma yapılmamış.' }
    ],
    'S7.3': [
      { score: 4, text: 'Farklı hedeflerde kök düğümün değiştiğini söyler VE biyolojik ya da istatistiksel yorum yapar.' },
      { score: 3, text: 'Değişikliği söyler, kısmi yorum.' },
      { score: 2, text: 'Değişikliği söyler, yorum yok.' },
      { score: 1, text: 'Belirsiz bir şekilde değinir.' },
      { score: 0, text: 'Yanıt yok veya kök düğüm karşılaştırması yok.' }
    ]
  };

  /* ---- helpers ---- */
  function h(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ---- per-criterion shuffled items ---- */
  function shuffledForCrit(crit) {
    var all = (root.COLAB_REVIEW_ITEMS || []).filter(function (x) { return x.criterion === crit; });
    if (!all.length) return all;
    var key = 'colabReview_shuffle_' + crit + '_v1';
    try {
      var stored = JSON.parse(sessionStorage.getItem(key) || 'null');
      if (stored && stored.length === all.length) {
        return stored.map(function (id) { return all.find(function (x) { return x.id === id; }); }).filter(Boolean);
      }
    } catch (e) {}
    var ids = all.map(function (x) { return x.id; });
    for (var i = ids.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = ids[i]; ids[i] = ids[j]; ids[j] = tmp;
    }
    try { sessionStorage.setItem(key, JSON.stringify(ids)); } catch (e) {}
    return ids.map(function (id) { return all.find(function (x) { return x.id === id; }); }).filter(Boolean);
  }

  function allItems() { return root.COLAB_REVIEW_ITEMS || []; }

  /* ---- stats ---- */
  function kappa(ratings) {
    var all = allItems();
    var rated = all.filter(function (it) { return ratings[it.id] != null; });
    if (rated.length < 2) return null;
    var n = rated.length;
    var human_dist = {}, machine_dist = {};
    rated.forEach(function (it) {
      var hs = ratings[it.id];
      var ms = it.machine_score;
      human_dist[hs] = (human_dist[hs] || 0) + 1;
      machine_dist[ms] = (machine_dist[ms] || 0) + 1;
    });
    var max_possible = Math.max.apply(null, rated.map(function (it) { return it.max; }));
    var Po = 0, Pe = 0;
    for (var i = 0; i <= max_possible; i++) {
      for (var j = 0; j <= max_possible; j++) {
        var w = 1 - Math.abs(i - j) / max_possible;
        var pi = (human_dist[i] || 0) / n;
        var pj = (machine_dist[j] || 0) / n;
        var obs = rated.filter(function (it) { return ratings[it.id] === i && it.machine_score === j; }).length / n;
        Po += w * obs;
        Pe += w * pi * pj;
      }
    }
    if (Pe >= 1) return 1;
    return (Po - Pe) / (1 - Pe);
  }

  function stats(ratings) {
    var all = allItems();
    var total = all.length;
    var done = all.filter(function (it) { return ratings[it.id] != null; }).length;
    var k = kappa(ratings);
    return { total: total, done: done, kappa: k };
  }

  /* ---- page ---- */
  function page() {
    if (!allItems().length) {
      return '<div class="page"><p>Review data not loaded.</p></div>';
    }
    return [
      '<div class="page wide colab-review-page">',
      '<p class="eyebrow">İnsan değerlendirmesi</p>',
      '<h1>Colab puanlama incelemesi</h1>',
      '<p>Her soru için tüm öğrencileri değerlendirin, sonra bir sonraki soruya geçin. Puanlarınız bu tarayıcıda saklanır.</p>',
      '<div class="cr-toolbar">',
      '  <button type="button" id="crExport" class="btn-secondary">JSON İndir</button>',
      '</div>',
      '<div id="crStats" class="cr-stats"></div>',
      '<div id="crCritHeader" class="cr-crit-header"></div>',
      '<div class="cr-layout">',
      '  <div id="crList" class="cr-list"></div>',
      '  <div id="crDetail" class="cr-detail"></div>',
      '</div>',
      '</div>'
    ].join('');
  }

  /* ---- bind ---- */
  function bind() {
    var container = document.querySelector('.colab-review-page');
    if (!container) return;

    var ratings = load();
    var critIdx = loadCritIdx();
    var currentId = null;

    var listEl = document.getElementById('crList');
    var detailEl = document.getElementById('crDetail');
    var statsEl = document.getElementById('crStats');
    var critHdrEl = document.getElementById('crCritHeader');

    function currentCrit() { return CRIT_ORDER[critIdx] || CRIT_ORDER[0]; }

    function critItems() { return shuffledForCrit(currentCrit()); }

    function allRatedForCrit() {
      return critItems().every(function (it) { return ratings[it.id] != null; });
    }

    function drawStats() {
      var s = stats(ratings);
      var pct = s.total ? Math.round(100 * s.done / s.total) : 0;
      var kStr = s.kappa != null ? s.kappa.toFixed(3) : 'n/a';
      statsEl.innerHTML =
        '<span class="cr-stat"><strong>' + s.done + ' / ' + s.total + '</strong> toplam değerlendirildi (' + pct + '%)</span>';
    }

    function goToCrit(idx) {
      critIdx = Math.max(0, Math.min(idx, CRIT_ORDER.length - 1));
      saveCritIdx(critIdx);
      currentId = null;
      drawCritHeader();
      drawList();
      drawDetail();
    }

    function drawCritHeader() {
      var crit = currentCrit();
      var total = CRIT_ORDER.length;
      var done = critItems().filter(function (it) { return ratings[it.id] != null; }).length;
      var all = critItems().length;
      var allDone = done === all;

      // Nav row
      var navHtml = '<div class="cr-crit-nav">';
      navHtml += '<button type="button" id="crPrevCrit" class="btn-secondary cr-crit-nav-btn"' + (critIdx === 0 ? ' disabled' : '') + '>← Önceki</button>';
      var crumbHtml = CRIT_ORDER.map(function (c, i) {
        var cnt = shuffledForCrit(c).filter(function (it) { return ratings[it.id] != null; }).length;
        var ttl = shuffledForCrit(c).length;
        var cls = 'cr-crumb' + (i === critIdx ? ' cr-crumb--active' : '') + (cnt === ttl && ttl > 0 ? ' cr-crumb--done' : '');
        return '<button type="button" class="' + cls + '" data-ci="' + i + '">' + h(Q_CODE[c] || c) + '</button>';
      }).join('');
      navHtml += '<div class="cr-crumbs">' + crumbHtml + '</div>';
      navHtml += '<button type="button" id="crNextCrit" class="btn-secondary cr-crit-nav-btn"' + (critIdx === CRIT_ORDER.length - 1 ? ' disabled' : '') + '>Sonraki →</button>';
      navHtml += '</div>';

      // Info row
      var infoHtml = '<div class="cr-crit-info">' +
        '<span class="cr-crit-step">Soru ' + (critIdx + 1) + ' / ' + total + '</span>' +
        '<span class="cr-crit-code">' + h(Q_CODE[crit] || crit) + '</span>' +
        '<span class="cr-crit-aicft">' + h(crit) + '</span>' +
        '<span class="cr-crit-label">' + h(TR_LABELS[crit] || crit) + '</span>' +
        '<span class="cr-crit-progress' + (allDone ? ' cr-crit-done' : '') + '">' + done + ' / ' + all + ' değerlendirildi</span>' +
        '</div>';

      critHdrEl.innerHTML = navHtml + infoHtml;

      document.getElementById('crPrevCrit').onclick = function () { goToCrit(critIdx - 1); };
      document.getElementById('crNextCrit').onclick = function () { goToCrit(critIdx + 1); };
      critHdrEl.querySelectorAll('.cr-crumb').forEach(function (btn) {
        btn.onclick = function () { goToCrit(parseInt(this.dataset.ci, 10)); };
      });
    }

    function drawList() {
      var its = critItems();
      listEl.replaceChildren();
      its.forEach(function (it) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cr-item' + (currentId === it.id ? ' cr-item--active' : '') +
          (ratings[it.id] != null ? ' cr-item--done' : '');
        var ratingStr = ratings[it.id] != null ? ratings[it.id] + '/' + it.max : '?/' + it.max;
        btn.innerHTML = '<span class="cr-item-num">' + (its.indexOf(it) + 1) + '</span>' +
          '<span class="cr-item-score cr-human">' + ratingStr + '</span>';
        btn.onclick = function () { currentId = it.id; drawList(); drawDetail(); };
        listEl.append(btn);
      });
      if (!its.length) {
        listEl.innerHTML = '<p class="cr-empty">Bu kriter için madde yok.</p>';
      }
    }

    function drawDetail() {
      detailEl.replaceChildren();
      if (!currentId) {
        detailEl.innerHTML = '<p class="cr-empty">Listeden bir madde seçin.</p>';
        return;
      }
      var it = critItems().find(function (x) { return x.id === currentId; });
      if (!it) return;

      var currentRating = ratings[it.id];
      var list = critItems();
      var idx = list.findIndex(function (x) { return x.id === currentId; });

      // Question prompt
      var qText = TR_QUESTIONS[it.criterion];
      if (qText) {
        var qSection = document.createElement('div');
        qSection.className = 'cr-section cr-question-section';
        qSection.innerHTML = '<h3>Soru</h3><div class="cr-question-text">' + h(qText) + '</div>';
        detailEl.append(qSection);
      }

      // Student text
      var textSection = document.createElement('div');
      textSection.className = 'cr-section';
      var autoCheckHtml = '';
      if (it.auto_check) {
        var icon = it.auto_check.condition_met ? '✓' : '✗';
        var cls = it.auto_check.condition_met ? 'cr-auto-pass' : 'cr-auto-fail';
        autoCheckHtml = '<p class="cr-auto-check ' + cls + '"><strong>Python kodu otomatik kontrol ' + icon + '</strong> ' + h(it.auto_check.detail) + '</p>';
      }
      textSection.innerHTML = '<h3>Öğrencinin yanıtı</h3>' +
        '<div class="cr-student-text">' + (it.student_text ? h(it.student_text) : '<em>Metin çıkarılamadı</em>') + '</div>' +
        autoCheckHtml;
      detailEl.append(textSection);

      // Rubric section
      var rubricList = TR_RUBRICS[it.criterion];
      if (rubricList) {
        var rubricSection = document.createElement('div');
        rubricSection.className = 'cr-section';
        var rubricRows = rubricList.map(function (r) {
          return '<tr><td class="cr-rub-score">' + r.score + '</td><td class="cr-rub-text">' + h(r.text) + '</td></tr>';
        }).join('');
        rubricSection.innerHTML = '<h3>Puanlama kriterleri</h3><table class="cr-rubric-table"><tbody>' + rubricRows + '</tbody></table>';
        detailEl.append(rubricSection);
      }

      // Human rating
      var ratingSection = document.createElement('div');
      ratingSection.className = 'cr-section cr-rating-section';
      var radioHtml = '';
      for (var v = 0; v <= it.max; v++) {
        var checked = currentRating === v ? ' checked' : '';
        radioHtml += '<label class="cr-radio"><input type="radio" name="crRating" value="' + v + '"' + checked + '> ' + v + '</label>';
      }
      ratingSection.innerHTML = '<h3>Değerlendirmeniz</h3><div class="cr-radios">' + radioHtml + '</div>';
      detailEl.append(ratingSection);

      // Nav buttons
      var nav = document.createElement('div');
      nav.className = 'cr-nav';
      var prevBtn = document.createElement('button');
      prevBtn.type = 'button'; prevBtn.className = 'btn-secondary'; prevBtn.textContent = 'Önceki';
      prevBtn.disabled = idx <= 0;
      prevBtn.onclick = function () {
        if (idx > 0) { currentId = list[idx - 1].id; drawList(); drawDetail(); }
      };
      var nextBtn = document.createElement('button');
      nextBtn.type = 'button'; nextBtn.className = 'btn-primary';
      nextBtn.textContent = idx < list.length - 1 ? 'Sonraki' : 'Bitti';
      nextBtn.onclick = function () {
        if (idx < list.length - 1) { currentId = list[idx + 1].id; drawList(); drawDetail(); }
      };
      nav.append(prevBtn, nextBtn);
      detailEl.append(nav);

      // Wire rating change
      ratingSection.querySelectorAll('input[name="crRating"]').forEach(function (radio) {
        radio.onchange = function () {
          ratings[it.id] = parseInt(this.value, 10);
          save(ratings);
          drawStats();
          drawCritHeader();
          drawList();
          if (idx < list.length - 1) {
            currentId = list[idx + 1].id;
            drawList();
            drawDetail();
          } else {
            drawDetail();
          }
        };
      });
    }

    document.getElementById('crExport').onclick = function () {
      var all = allItems();
      var output = all.map(function (it) {
        return {
          id: it.id, student: it.student, criterion: it.criterion,
          max: it.max, machine_score: it.machine_score,
          human_score: ratings[it.id] != null ? ratings[it.id] : null
        };
      });
      var blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'colab_human_ratings.json';
      a.click();
    };

    drawStats();
    drawCritHeader();
    drawList();
    drawDetail();
  }

  root.ColabReview = { page: page, bind: bind };
})(window);
