/* Colab scoring human-validation review interface */
(function (root) {
  'use strict';

  var STORAGE_KEY = 'colabReview_v1';

  /* ---- persistence ---- */
  function load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch (e) { return {}; }
  }
  function save(ratings) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(ratings)); } catch (e) {}
  }

  /* ---- criterion labels (Turkish) ---- */
  var TR_LABELS = {
    'S1.3': 'VKA: Habitat dengesizliğinin etkisi (3p)',
    'S1.4': 'VKA: Türlere göre vücut kütlesi karşılaştırması (3p)',
    'S2.2': 'Araştırma sorusu kalitesi (2p)',
    'S3.1': 'Bölme parametreleri: stratify + test_size (2p)',
    'S3.2': 'Stratify kaldırmanın kavramsal etkisi (2p)',
    'S3.3': 'Rastgelelik ve yeniden üretilebilirlik (1p)',
    'S6.1': 'Yansıma S6.1: En önemli öğrenme (3p)',
    'S6.2': 'Yansıma S6.2: Doğruluk yetersizliğinin nedeni (3p)',
    'S6.3': 'Yansıma S6.3: Derinlik hiperparametresi (2p)',
    'S6.4': 'Yansıma S6.4: Farklı sonuç tahmini (3p)',
    'S7.2': 'Çapraz karşılaştırma: örüntü akıl yürütme (3p)',
    'S7.3': 'Çapraz karşılaştırma: Fasıl tartışması (2p)'
  };
  var TR_MODE = { 'llm': 'LLM', 'hybrid': 'Karma', 'auto': 'Otomatik' };

  /* ---- question prompts shown to students (Turkish) ---- */
  var TR_QUESTIONS = {
    'S1.3': 'Habitat sınıflarındaki dengesizlik (Yer çok, Ağaç az) modelin tahminlerini nasıl etkiler? Hangi sınıf daha iyi tahmin edilir, neden?',
    'S1.4': 'Türlere göre vücut kütlesi dağılımına baktığında hangi tür en ağır, hangi tür en hafif? Biyolojik bir açıklama yapabilir misin?',
    'S2.2': 'Bu veri setiyle test etmek istediğin araştırma sorularını yaz. Her hedef değişken (YaşamAlanı, Tür, Cinsiyet) için ayrı bir araştırma sorusu oluştur.',
    'S3.1': 'train_test_split fonksiyonunda test_size, stratify ve random_state parametrelerini nasıl ayarladın? (Beklenen: test_size=0.2, stratify=y, random_state=42)',
    'S3.2': 'Eğer stratify parametresini kaldırırsan ne olur? Sınıf dağılımı üzerindeki etkisini açıkla.',
    'S3.3': 'random_state parametresini değiştirirsen sonuçlar nasıl değişir? Bu parametrenin rolü nedir?',
    'S6.1': 'Soru 1 — Bu ödevde veri kartları, CODAP ve Python olmak üç farklı ortamda çalıştın. Her birinde ne öğrendiğini ve hangi hataları fark ettiğini açıkla.',
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
      { score: 1, text: 'random_state\'in karıştırma tohumunu kontrol ettiğini, değiştirmenin farklı bir train/test bölmesi ürettiğini ama modelin her çalıştırmada tekrarlanabilir kaldığını açıklar.' },
      { score: 0, text: 'Yanıt yok veya yanlış.' }
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

  var SHUFFLE_KEY = 'colabReview_shuffle_v1';

  function shuffledItems() {
    var all = (root.COLAB_REVIEW_ITEMS || []);
    if (!all.length) return all;
    try {
      var stored = JSON.parse(sessionStorage.getItem(SHUFFLE_KEY) || 'null');
      if (stored && stored.length === all.length) {
        return stored.map(function (id) { return all.find(function (x) { return x.id === id; }); }).filter(Boolean);
      }
    } catch (e) {}
    // Fisher-Yates shuffle
    var ids = all.map(function (x) { return x.id; });
    for (var i = ids.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = ids[i]; ids[i] = ids[j]; ids[j] = tmp;
    }
    try { sessionStorage.setItem(SHUFFLE_KEY, JSON.stringify(ids)); } catch (e) {}
    return ids.map(function (id) { return all.find(function (x) { return x.id === id; }); }).filter(Boolean);
  }

  function items() {
    return shuffledItems();
  }

  /* ---- stats ---- */
  function kappa(ratings) {
    var all = items();
    var rated = all.filter(function (it) { return ratings[it.id] != null; });
    if (rated.length < 2) return null;
    var n = rated.length;
    var sum_agree = 0, sum_chance = 0;
    // Build 2D confusion: treat each item as a 0..max scale
    // Use simple Cohen's kappa (linear, not weighted) over discretised agreement
    // Weighted kappa (linear weights) across the full integer range
    var total_max = rated.reduce(function (s, it) { return s + it.max; }, 0);
    var sum_w_agree = 0, sum_w_chance = 0;
    // distribution over scores for each rater
    var score_range = {};
    rated.forEach(function (it) {
      for (var v = 0; v <= it.max; v++) {
        score_range[v] = (score_range[v] || 0);
      }
    });
    var human_dist = {}, machine_dist = {};
    rated.forEach(function (it) {
      var h_score = ratings[it.id];
      var m_score = it.machine_score;
      human_dist[h_score] = (human_dist[h_score] || 0) + 1;
      machine_dist[m_score] = (machine_dist[m_score] || 0) + 1;
    });
    // Compute weighted kappa (linear weights)
    var max_possible = Math.max.apply(null, rated.map(function(it){return it.max;}));
    var Po = 0, Pe = 0;
    for (var i = 0; i <= max_possible; i++) {
      for (var j = 0; j <= max_possible; j++) {
        var w = 1 - Math.abs(i - j) / max_possible;
        var pi = (human_dist[i] || 0) / n;
        var pj = (machine_dist[j] || 0) / n;
        // observed: count pairs where human=i and machine=j
        var obs = rated.filter(function(it){ return ratings[it.id] === i && it.machine_score === j; }).length / n;
        Po += w * obs;
        Pe += w * pi * pj;
      }
    }
    if (Pe >= 1) return 1;
    return (Po - Pe) / (1 - Pe);
  }

  function stats(ratings) {
    var all = items();
    var total = all.length;
    var done = all.filter(function (it) { return ratings[it.id] != null; }).length;
    var k = kappa(ratings);
    var agreements = all.filter(function (it) {
      return ratings[it.id] != null && ratings[it.id] === it.machine_score;
    }).length;
    return { total: total, done: done, agreements: agreements, kappa: k };
  }

  /* ---- page ---- */
  function page() {
    var all = items();
    if (!all.length) {
      return '<div class="page"><p>Review data not loaded.</p></div>';
    }
    var students = [];
    var seen = {};
    all.forEach(function (it) {
      if (!seen[it.student]) { seen[it.student] = true; students.push(it.student); }
    });
    var studentOpts = students.map(function (s) {
      return '<option value="' + h(s) + '">' + h(s) + '</option>';
    }).join('');
    var critOpts = [];
    var seenC = {};
    all.forEach(function (it) {
      if (!seenC[it.criterion]) {
        seenC[it.criterion] = true;
        critOpts.push('<option value="' + h(it.criterion) + '">' + h(it.criterion) + ' — ' + h(TR_LABELS[it.criterion] || it.label) + '</option>');
      }
    });
    return [
      '<div class="page wide colab-review-page">',
      '<p class="eyebrow">İnsan değerlendirmesi</p>',
      '<h1>Colab puanlama incelemesi</h1>',
      '<p>Her maddeyi bağımsız olarak değerlendirin. Puanlarınız bu tarayıcıda saklanır. Bitirince Cohen κ analizi için Export butonuyla indirin.</p>',
      '<div class="cr-toolbar">',
      '  <label>Öğrenciye göre <select id="crStudent"><option value="">Tüm öğrenciler</option>' + studentOpts + '</select></label>',
      '  <label>Ölçüte göre <select id="crCrit"><option value="">Tüm ölçütler</option>' + critOpts.join('') + '</select></label>',
      '  <label><input type="checkbox" id="crUnrated"> Sadece değerlendirilmeyenler</label>',
      '  <button type="button" id="crExport" class="btn-secondary">JSON İndir</button>',
      '  <button type="button" id="crReset" class="btn-secondary cr-danger">Sıfırla</button>',
      '</div>',
      '<div id="crStats" class="cr-stats"></div>',
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
    var currentId = null;
    var filterStudent = '';
    var filterCrit = '';
    var filterUnrated = false;

    var listEl = document.getElementById('crList');
    var detailEl = document.getElementById('crDetail');
    var statsEl = document.getElementById('crStats');

    function filtered() {
      return items().filter(function (it) {
        if (filterStudent && it.student !== filterStudent) return false;
        if (filterCrit && it.criterion !== filterCrit) return false;
        if (filterUnrated && ratings[it.id] != null) return false;
        return true;
      });
    }

    function drawStats() {
      var s = stats(ratings);
      var pct = s.total ? Math.round(100 * s.done / s.total) : 0;
      var kStr = s.kappa != null ? s.kappa.toFixed(3) : 'n/a';
      var agrStr = s.done ? Math.round(100 * s.agreements / s.done) + '%' : 'n/a';
      statsEl.innerHTML =
        '<span class="cr-stat"><strong>' + s.done + ' / ' + s.total + '</strong> değerlendirildi (' + pct + '%)</span>' +
        '<span class="cr-stat"><strong>' + agrStr + '</strong> tam uyum</span>' +
        '<span class="cr-stat">Ağırlıklı κ <strong>' + kStr + '</strong></span>';
    }

    function drawList() {
      var items = filtered();
      listEl.replaceChildren();
      items.forEach(function (it) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cr-item' + (currentId === it.id ? ' cr-item--active' : '') +
          (ratings[it.id] != null ? (ratings[it.id] === it.machine_score ? ' cr-item--agree' : ' cr-item--disagree') : '');
        var ratingStr = ratings[it.id] != null ? ratings[it.id] + '/' + it.max : '?/' + it.max;
        btn.innerHTML = '<span class="cr-item-crit">' + h(it.criterion) + '</span>' +
          '<span class="cr-item-score cr-human">H:' + ratingStr + '</span>';
        btn.onclick = function () { currentId = it.id; drawList(); drawDetail(); };
        listEl.append(btn);
      });
      if (!items.length) {
        listEl.innerHTML = '<p class="cr-empty">Filtreye uyan madde yok.</p>';
      }
    }

    function drawDetail() {
      detailEl.replaceChildren();
      if (!currentId) {
        detailEl.innerHTML = '<p class="cr-empty">Listeden bir madde seçin.</p>';
        return;
      }
      var it = items().find(function (x) { return x.id === currentId; });
      if (!it) return;

      var currentRating = ratings[it.id];
      var list = filtered();
      var idx = list.findIndex(function (x) { return x.id === currentId; });

      // Header
      var hdr = document.createElement('div');
      hdr.className = 'cr-detail-header';
      hdr.innerHTML =
        '<h2>' + h(it.criterion) + '</h2>' +
        '<p class="cr-label">' + h(TR_LABELS[it.criterion] || it.label) + ' <span class="cr-mode">' + h(TR_MODE[it.mode] || it.mode) + '</span></p>';
      detailEl.append(hdr);

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
        autoCheckHtml = '<p class="cr-auto-check ' + cls + '"><strong>Otomatik kontrol ' + icon + '</strong> ' + h(it.auto_check.detail) + '</p>';
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

      // Machine justification (no score number shown — blind rating)
      var machineSection = document.createElement('div');
      machineSection.className = 'cr-section';
      machineSection.innerHTML = '<h3>Sistem gerekçesi</h3>' +
        '<div class="cr-justification">' + h(it.justification) + '</div>';
      if (it.flag) {
        machineSection.innerHTML += '<p class="cr-flag">Not: ' + h(it.flag) + '</p>';
      }
      detailEl.append(machineSection);

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
      nextBtn.type = 'button'; nextBtn.className = 'btn-primary'; nextBtn.textContent = idx < list.length - 1 ? 'Sonraki' : 'Bitti';
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
          drawList();
          // Auto-advance after rating
          if (idx < list.length - 1) {
            currentId = list[idx + 1].id;
            drawList();
            drawDetail();
          }
        };
      });
    }

    // Toolbar events
    document.getElementById('crStudent').onchange = function () {
      filterStudent = this.value; currentId = null; drawList(); drawDetail();
    };
    document.getElementById('crCrit').onchange = function () {
      filterCrit = this.value; currentId = null; drawList(); drawDetail();
    };
    document.getElementById('crUnrated').onchange = function () {
      filterUnrated = this.checked; currentId = null; drawList(); drawDetail();
    };
    document.getElementById('crExport').onclick = function () {
      var all = items();
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
    document.getElementById('crReset').onclick = function () {
      if (!confirm('Tüm puanlarınız silinecek. Geri alınamaz. Devam edilsin mi?')) return;
      ratings = {};
      save(ratings);
      currentId = null;
      drawStats(); drawList(); drawDetail();
    };

    drawStats();
    drawList();
    drawDetail();
  }

  root.ColabReview = { page: page, bind: bind };
})(window);
