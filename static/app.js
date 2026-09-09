// Akakçe Fiyat Takip & Alarm JavaScript İstemcisi

let priceChart = null;
let currentChartProductId = null;
let activeTab = 'reports';

document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
  // Her 30 saniyede bir verileri sessizce tazele
  setInterval(refreshDashboardData, 30000);
});

async function initDashboard() {
  await loadStatus();
  await loadProducts();
  await loadReports();
  await loadAlarms();
  lucide.createIcons();
}

async function refreshDashboardData() {
  await loadStatus();
  await loadProducts(false);
  if (activeTab === 'reports') await loadReports();
  if (activeTab === 'alarms') await loadAlarms();
  if (currentChartProductId) await loadProductChart(currentChartProductId, false);
}

// 1. Sistem Durumu
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    
    document.getElementById('statReportTime').innerText = `Her gün saat ${data.daily_report_time}`;
    document.getElementById('statInterval').innerText = `Her ${data.check_interval_minutes} dk kontrol`;
    document.getElementById('statProductCount').innerText = `${data.total_products} Ürün (${data.active_products} Aktif)`;
    
    const channels = [];
    if (data.desktop_enabled) channels.push('Masaüstü');
    if (data.telegram_enabled) channels.push('Telegram');
    if (data.discord_enabled) channels.push('Discord');
    document.getElementById('statNotifChannels').innerText = channels.length > 0 ? channels.join(', ') : 'Devre Dışı';
  } catch (err) {
    console.error('Durum yüklenemedi:', err);
  }
}

// 2. Ürün Kartları
let allProductsList = [];
let currentCategoryFilter = 'all';

async function loadProducts(rebuildChartSelect = true) {
  try {
    const res = await fetch('/api/products');
    allProductsList = await res.json();
    
    if (!allProductsList || allProductsList.length === 0) {
      const container = document.getElementById('productCardsContainer');
      if (container) container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-500 text-sm">Takip edilen ürün bulunamadı.</div>`;
      return;
    }
    
    updateCategoryCounts();

    if (rebuildChartSelect) {
      populateChartDropdown(allProductsList);
    }

    renderFilteredProductCards();

    // URL parametresinden kategori filtresi varsa uygula (örn: ?cat=deals_20)
    const urlParams = new URLSearchParams(window.location.search);
    const initialCat = urlParams.get('cat');
    if (initialCat) {
      filterProductsByCategory(initialCat);
    }

    // İlk ürünün grafiğini yükle
    if (rebuildChartSelect && allProductsList.length > 0 && !currentChartProductId) {
      currentChartProductId = allProductsList[0].id;
      const chartSelect = document.getElementById('chartProductSelect');
      if (chartSelect) chartSelect.value = currentChartProductId;
      await loadProductChart(currentChartProductId);
    }
  } catch (err) {
    console.error('Ürünler yüklenirken hata:', err);
  }
}

function updateCategoryCounts() {
  if (!allProductsList) return;
  const countAll = allProductsList.length;
  const countLast6m = allProductsList.filter(p => p.is_last_6m_lowest).length;
  const countDeals = allProductsList.filter(p => p.is_featured_deal || (p.discount_percent && p.discount_percent >= 20)).length;
  const countMON = allProductsList.filter(p => (p.category || '').includes('Monitör')).length;
  const countCLIMA = allProductsList.filter(p => (p.category || '').includes('Klima') || (p.category || '').includes('Vantilatör') || (p.category || '').includes('Hava') || (p.category || '').includes('Isı')).length;
  const countHOME = allProductsList.filter(p => (p.category || '').includes('Beyaz Eşya') || (p.category || '').includes('Buzdolabı') || (p.category || '').includes('Süpürge') || (p.category || '').includes('Mutfak') || (p.category || '').includes('Çay') || (p.category || '').includes('Blender') || (p.category || '').includes('Düdüklü') || (p.category || '').includes('Hamur')).length;
  const countWATCH = allProductsList.filter(p => (p.category || '').includes('Saat')).length;
  const countCARE = allProductsList.filter(p => (p.category || '').includes('Bakım') || (p.category || '').includes('Masaj') || (p.category || '').includes('Saç')).length;
  const countTOY = allProductsList.filter(p => (p.category || '').includes('Oyuncak') || (p.category || '').includes('Hobi')).length;
  const countBIKE = allProductsList.filter(p => (p.category || '').includes('Bisiklet') || (p.category || '').includes('Spor') || (p.category || '').includes('Scooter')).length;
  const countRAM = allProductsList.filter(p => (p.category || '').includes('RAM') || (p.category || '').includes('Bellek')).length;
  const countPC = allProductsList.filter(p => (p.category || '').includes('Bilgisayar') || (p.category || '').includes('Laptop')).length;
  const countSSD = allProductsList.filter(p => (p.category || '').includes('SSD') || (p.category || '').includes('Depolama')).length;
  const countCPU = allProductsList.filter(p => (p.category || '').includes('İşlemci') || (p.category || '').includes('Anakart')).length;
  const countCABLE = allProductsList.filter(p => (p.category || '').includes('Kablo') || (p.category || '').includes('Dönüştürücü') || (p.category || '').includes('HDMI')).length;
  const countACC = allProductsList.filter(p => (p.category || '').includes('Çevre') || (p.category || '').includes('Kulaklık') || (p.category || '').includes('Mouse') || (p.category || '').includes('Yazıcı') || (p.category || '').includes('Takip')).length;

  const setT = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
  setT('catCount_all', countAll);
  setT('catCount_last_6m', countLast6m);
  setT('catCount_deals', countDeals);
  setT('catCount_MON', countMON);
  setT('catCount_CLIMA', countCLIMA);
  setT('catCount_HOME', countHOME);
  setT('catCount_WATCH', countWATCH);
  setT('catCount_CARE', countCARE);
  setT('catCount_TOY', countTOY);
  setT('catCount_BIKE', countBIKE);
  setT('catCount_RAM', countRAM);
  setT('catCount_PC', countPC);
  setT('catCount_SSD', countSSD);
  setT('catCount_CPU', countCPU);
  setT('catCount_CABLE', countCABLE);
  setT('catCount_ACC', countACC);
}

function filterProductsByCategory(category) {
  currentCategoryFilter = category;
  
  const btnMap = {
    'all': 'catBtn_all',
    'last_6m': 'catBtn_last_6m',
    'deals_20': 'catBtn_deals',
    'Monitör & Ekran': 'catBtn_MON',
    'Klima & Isıtma': 'catBtn_CLIMA',
    'Beyaz Eşya & Ev Aletleri': 'catBtn_HOME',
    'SSD & Depolama': 'catBtn_SSD',
    'RAM & Bellek': 'catBtn_RAM',
    'Kablo & Dönüştürücü': 'catBtn_CABLE',
    'Bilgisayar & Laptop': 'catBtn_PC',
    'Saat & Aksesuar': 'catBtn_WATCH',
    'Kişisel Bakım & Sağlık': 'catBtn_CARE',
    'Çevre Birimleri': 'catBtn_ACC',
    'İşlemci & Anakart': 'catBtn_CPU',
    'Oyuncak & Hobi': 'catBtn_TOY',
    'Bisiklet & Spor': 'catBtn_BIKE'
  };
  
  Object.entries(btnMap).forEach(([cat, id]) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (cat === category) {
      if (cat === 'deals_20') {
        el.className = 'category-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-amber-500 text-slate-950 shadow-md transition flex items-center space-x-1.5';
      } else if (cat === 'last_6m') {
        el.className = 'category-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-cyan-500 text-slate-950 shadow-md transition flex items-center space-x-1.5';
      } else {
        el.className = 'category-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-sm transition flex items-center space-x-1.5';
      }
    } else {
      if (cat === 'deals_20') {
        el.className = 'category-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-amber-500/20 via-orange-500/20 to-rose-500/20 hover:from-amber-500/30 hover:to-rose-500/30 text-amber-300 border border-amber-500/40 transition shadow-sm flex items-center space-x-1.5';
      } else if (cat === 'last_6m') {
        el.className = 'category-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-indigo-500/20 hover:from-cyan-500/30 hover:to-indigo-500/30 text-cyan-300 border border-cyan-500/40 transition shadow-sm flex items-center space-x-1.5';
      } else {
        el.className = 'category-btn px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition flex items-center space-x-1.5';
      }
    }
  });

  renderFilteredProductCards();
}

function populateChartDropdown(products) {
  const chartSelect = document.getElementById('chartProductSelect');
  if (!chartSelect) return;
  chartSelect.innerHTML = '';
  
  const categoryConfigs = [
    { label: '📉 Son 6 Ayın En Düşükleri', filter: p => p.is_last_6m_lowest },
    { label: '🔥 %20+ İndirim Fırsatları', filter: p => p.is_featured_deal || (p.discount_percent && p.discount_percent >= 20) },
    { label: '🖥️ Monitör & Ekran', filter: p => (p.category || '').includes('Monitör') },
    { label: '❄️ Klima & Isıtma', filter: p => (p.category || '').includes('Klima') || (p.category || '').includes('Vantilatör') || (p.category || '').includes('Hava') || (p.category || '').includes('Isı') },
    { label: '🏠 Beyaz Eşya & Ev Aletleri', filter: p => (p.category || '').includes('Beyaz Eşya') || (p.category || '').includes('Buzdolabı') || (p.category || '').includes('Süpürge') || (p.category || '').includes('Mutfak') || (p.category || '').includes('Çay') || (p.category || '').includes('Blender') },
    { label: '💾 SSD & Depolama', filter: p => (p.category || '').includes('SSD') || (p.category || '').includes('Depolama') },
    { label: '⚡ RAM & Bellek', filter: p => (p.category || '').includes('RAM') || (p.category || '').includes('Bellek') },
    { label: '🔌 Kablo & Dönüştürücü', filter: p => (p.category || '').includes('Kablo') || (p.category || '').includes('Dönüştürücü') || (p.category || '').includes('HDMI') },
    { label: '💻 Bilgisayar & Laptop', filter: p => (p.category || '').includes('Bilgisayar') || (p.category || '').includes('Laptop') },
    { label: '⌚ Saat & Aksesuar', filter: p => (p.category || '').includes('Saat') },
    { label: '✨ Kişisel Bakım & Sağlık', filter: p => (p.category || '').includes('Bakım') || (p.category || '').includes('Masaj') || (p.category || '').includes('Saç') },
    { label: '🧸 Oyuncak & Hobi', filter: p => (p.category || '').includes('Oyuncak') || (p.category || '').includes('Hobi') },
    { label: '🚲 Bisiklet & Spor', filter: p => (p.category || '').includes('Bisiklet') || (p.category || '').includes('Spor') },
    { label: '⚡ İşlemci & Anakart', filter: p => (p.category || '').includes('İşlemci') || (p.category || '').includes('Anakart') },
    { label: '🎧 Çevre Birimleri', filter: p => (p.category || '').includes('Çevre') || (p.category || '').includes('Kulaklık') || (p.category || '').includes('Mouse') || (p.category || '').includes('Yazıcı') || (p.category || '').includes('Takip') }
  ];

  categoryConfigs.forEach(cfg => {
    const prods = products.filter(cfg.filter);
    if (prods.length > 0) {
      const group = document.createElement('optgroup');
      group.label = cfg.label;
      prods.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        const dealPrefix = (p.is_featured_deal || (p.discount_percent >= 20)) ? `[-%${Math.round(p.discount_percent)} Fırsat] ` : '';
        opt.textContent = `${dealPrefix}${p.name} - ${p.price_str || (p.price ? p.price + ' TL' : '')}`;
        group.appendChild(opt);
      });
      chartSelect.appendChild(group);
    }
  });
}

function renderFilteredProductCards() {
  const container = document.getElementById('productCardsContainer');
  if (!container) return;

  let products = allProductsList;
  if (currentCategoryFilter === 'deals_20') {
    products = allProductsList.filter(p => p.is_featured_deal || (p.discount_percent && p.discount_percent >= 20));
  } else if (currentCategoryFilter === 'last_6m') {
    products = allProductsList.filter(p => p.is_last_6m_lowest);
  } else if (currentCategoryFilter !== 'all') {
    products = allProductsList.filter(p => {
      const pCat = p.category || '';
      if (currentCategoryFilter === 'Monitör & Ekran') return pCat.includes('Monitör');
      if (currentCategoryFilter === 'Klima & Isıtma') return pCat.includes('Klima') || pCat.includes('Vantilatör') || pCat.includes('Hava') || pCat.includes('Isı');
      if (currentCategoryFilter === 'Beyaz Eşya & Ev Aletleri') return pCat.includes('Beyaz Eşya') || pCat.includes('Buzdolabı') || pCat.includes('Süpürge') || pCat.includes('Mutfak') || pCat.includes('Çay') || pCat.includes('Blender') || pCat.includes('Düdüklü') || pCat.includes('Hamur');
      if (currentCategoryFilter === 'Saat & Aksesuar') return pCat.includes('Saat');
      if (currentCategoryFilter === 'Kişisel Bakım & Sağlık') return pCat.includes('Bakım') || pCat.includes('Masaj') || pCat.includes('Saç');
      if (currentCategoryFilter === 'Kablo & Dönüştürücü') return pCat.includes('Kablo') || pCat.includes('Dönüştürücü') || pCat.includes('HDMI');
      if (currentCategoryFilter === 'Oyuncak & Hobi') return pCat.includes('Oyuncak') || pCat.includes('Hobi');
      if (currentCategoryFilter === 'Bisiklet & Spor') return pCat.includes('Bisiklet') || pCat.includes('Spor') || pCat.includes('Scooter');
      if (currentCategoryFilter === 'RAM & Bellek') return pCat.includes('RAM') || pCat.includes('Bellek');
      if (currentCategoryFilter === 'Bilgisayar & Laptop') return pCat.includes('Bilgisayar') || pCat.includes('Laptop');
      if (currentCategoryFilter === 'SSD & Depolama') return pCat.includes('SSD') || pCat.includes('Depolama');
      if (currentCategoryFilter === 'İşlemci & Anakart') return pCat.includes('İşlemci') || pCat.includes('Anakart');
      if (currentCategoryFilter === 'Çevre Birimleri') return pCat.includes('Çevre') || pCat.includes('Kulaklık') || pCat.includes('Mouse') || pCat.includes('Yazıcı') || pCat.includes('Takip');
      return pCat.includes(currentCategoryFilter);
    });
  }

  if (!products || products.length === 0) {
    container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-500 text-sm">Bu kategoride gösterilecek ürün bulunamadı.</div>`;
    return;
  }

  container.innerHTML = '';

  products.forEach((p) => {
    // Değişim rozeti
    let diffBadge = '';
    if (p.price_diff < 0) {
      diffBadge = `
        <span class="inline-flex items-center text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <i data-lucide="arrow-down-right" class="w-3 h-3 mr-0.5"></i>
          -${Math.abs(p.price_diff).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL (%${Math.abs(p.price_diff_percent)})
        </span>`;
    } else if (p.price_diff > 0) {
      diffBadge = `
        <span class="inline-flex items-center text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <i data-lucide="arrow-up-right" class="w-3 h-3 mr-0.5"></i>
          +${p.price_diff.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL (+%${p.price_diff_percent})
        </span>`;
    } else {
      diffBadge = `
        <span class="inline-flex items-center text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          Düne göre sabit
        </span>`;
    }

    // Eşik uyarısı rozeti
    const isThresholdHit = p.is_below_threshold;
    const thresholdFormatted = p.threshold_price > 0 
      ? `${p.threshold_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL`
      : 'Eşik Yok';

    // En Ucuz 3 Satıcı Listesi Hazırlığı
    const topSellers = (p.top_sellers && p.top_sellers.length > 0)
      ? p.top_sellers
      : [{
          seller_name: p.current_seller || 'En Ucuz Satıcı',
          seller_logo: '',
          price: p.current_price,
          price_str: p.current_price_str,
          cargo: p.cargo_info || 'Ücretsiz Kargo',
          url: p.direct_link || p.url
        }];

    const medalBadges = [
      { badge: '🥇 1.', color: 'border-amber-500/30 bg-amber-500/10 text-amber-300' },
      { badge: '🥈 2.', color: 'border-slate-500/30 bg-slate-500/10 text-slate-300' },
      { badge: '🥉 3.', color: 'border-amber-700/30 bg-amber-800/10 text-amber-500' }
    ];

    let topSellersHtml = '';
    topSellers.slice(0, 3).forEach((s, idx) => {
      const medal = medalBadges[idx] || { badge: `${idx + 1}.`, color: 'border-slate-700 bg-slate-800 text-slate-400' };
      const sPrice = s.price_str || (s.price ? `${s.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL` : '-');
      const sCargo = s.cargo || 'Ücretsiz Kargo';
      const sLogo = s.seller_logo 
        ? `<img src="${s.seller_logo}" alt="${s.seller_name}" class="h-3.5 max-w-[60px] object-contain shrink-0 rounded" onerror="this.style.display='none'">`
        : '';

      topSellersHtml += `
        <div class="flex items-center justify-between p-2 rounded-xl border border-slate-800/80 bg-slate-900/60 hover:border-emerald-500/40 hover:bg-slate-850 transition duration-150 text-xs">
          <div class="flex items-center space-x-2 min-w-0 pr-1.5">
            <span class="text-[10px] font-black px-1.5 py-0.5 rounded-md border ${medal.color} shrink-0">
              ${medal.badge}
            </span>
            <div class="min-w-0">
              <div class="flex items-center space-x-1.5">
                ${sLogo}
                <span class="font-bold text-slate-200 text-xs truncate" title="${s.seller_name}">
                  ${s.seller_name}
                </span>
              </div>
              <span class="text-[10px] text-emerald-400 block truncate font-medium">${s.cargo}</span>
            </div>
          </div>
          <div class="flex items-center space-x-2 shrink-0">
            <span class="font-black text-slate-100 text-xs">${sPrice}</span>
            <a href="${s.url}" target="_blank" class="inline-flex items-center justify-center p-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-white text-[10px] font-semibold transition hover:scale-105 shadow-sm" title="${s.seller_name} Mağazasına Git">
              <i data-lucide="shopping-bag" class="w-3 h-3"></i>
            </a>
          </div>
        </div>
      `;
    });

    const localImg = `/static/product_imgs/${p.id}.jpg`;
    const remoteImg = p.image_url || '/static/logo.png';
    const isDeal = p.is_featured_deal || (p.discount_percent && p.discount_percent >= 20);
    const dealPct = Math.round(p.discount_percent || 0);

    const card = document.createElement('div');
    card.className = `product-card bg-slate-900/60 border ${isThresholdHit ? 'threshold-alert-active border-rose-500/80 bg-rose-950/20' : (isDeal ? 'border-amber-500/40 shadow-lg shadow-amber-950/20' : 'border-slate-800/80')} rounded-2xl p-4 sm:p-5 flex flex-col justify-between relative overflow-hidden group hover:border-slate-700/80 transition`;

    card.innerHTML = `
      ${isThresholdHit ? `
        <div class="absolute top-0 right-0 bg-rose-600 text-white text-[10px] font-extrabold px-3 py-1 rounded-bl-xl shadow-lg flex items-center space-x-1 animate-pulse z-10">
          <i data-lucide="alert-triangle" class="w-3 h-3"></i>
          <span>HEDEF FİYATIN ALTINDA!</span>
        </div>
      ` : ''}

      <div>
        ${p.is_last_6m_lowest ? `
          <div class="mb-3 flex items-center justify-between px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500/20 via-blue-500/15 to-indigo-500/20 border border-cyan-500/50 shadow-md">
            <div class="flex items-center space-x-1.5">
              <span class="text-sm">📉</span>
              <span class="text-xs font-black text-cyan-300 tracking-wide">
                SON 6 AYIN EN DÜŞÜK FİYATI
              </span>
            </div>
            <span class="text-[10px] font-extrabold text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded-md border border-cyan-500/30">
              Akakçe Onaylı
            </span>
          </div>
        ` : (isDeal ? `
          <div class="mb-3 flex items-center justify-between px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500/20 via-orange-500/15 to-rose-500/20 border border-amber-500/50 shadow-md">
            <div class="flex items-center space-x-1.5">
              <span class="text-sm">🔥</span>
              <span class="text-xs font-black text-amber-300 tracking-wide">
                %${dealPct} BÜYÜK İNDİRİM
              </span>
            </div>
            <span class="text-[10px] font-extrabold text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded-md border border-amber-500/30">
              Ortalama Altı
            </span>
          </div>
        ` : '')}

        <!-- Kart Üst Rozetler ve Aktiflik (Görseli Asla Örtmez) -->
        <div class="flex items-center justify-between mb-2.5 px-0.5">
          <div class="flex items-center space-x-1.5 flex-wrap">
            <span class="px-2.5 py-0.5 rounded-lg bg-slate-800/90 text-blue-400 text-[10px] font-bold border border-blue-500/30 shadow-sm">
              ${p.category || 'Donanım'}
            </span>
            <span class="px-2.5 py-0.5 rounded-lg bg-slate-800/90 text-emerald-400 text-[10px] font-bold border border-emerald-500/30 shadow-sm">
              ${p.capacity || 'Standart'}
            </span>
          </div>
          <div>
            ${p.is_active ? `
              <span class="inline-flex items-center px-2 py-0.5 rounded-lg bg-emerald-950/90 border border-emerald-500/40 text-emerald-400 text-[10px] font-semibold shadow-sm">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>Aktif
              </span>
            ` : `
              <span class="px-2 py-0.5 rounded-lg bg-slate-800 text-slate-500 text-[10px] font-semibold border border-slate-700 shadow-sm">Duraklatıldı</span>
            `}
          </div>
        </div>

        <!-- Orijinal Ürün Görseli Stüdyo Vitrini (Kusursuz Beyaz Zemin, Bozulmasız Oran) -->
        <div onclick="openProductImageModal('${p.id}')" 
             class="relative w-full h-48 bg-white rounded-2xl overflow-hidden border border-slate-700/50 flex items-center justify-center p-3.5 mb-3.5 shadow-inner group/img cursor-pointer hover:border-emerald-500/60 hover:shadow-lg transition duration-300"
             title="Büyük Boyutta İncelemek İçin Tıklayın">
          <img src="${localImg}" 
               alt="${p.name}" 
               class="max-h-full max-w-full object-contain filter drop-shadow-sm transition-transform duration-300 group-hover/img:scale-105 select-none"
               loading="lazy"
               onerror="this.onerror=null;this.src='${remoteImg}'">
          
          <!-- Büyüt İpucu Rozeti -->
          <div class="absolute bottom-2 right-2 opacity-0 group-hover/img:opacity-100 transition duration-200 bg-slate-900/90 backdrop-blur text-white text-[10px] font-bold px-2 py-1 rounded-lg flex items-center space-x-1 shadow-md border border-slate-700 pointer-events-none">
            <i data-lucide="zoom-in" class="w-3 h-3 text-emerald-400"></i>
            <span>Büyük Görsel</span>
          </div>
        </div>

        <!-- Ürün Başlığı -->
        <h3 class="font-bold text-slate-100 text-sm leading-snug line-clamp-1 mb-2 hover:text-emerald-400 transition cursor-pointer" onclick="openProductImageModal('${p.id}')" title="${p.name}">
          ${p.name}
        </h3>

        <!-- Fiyat Bilgisi & Değişim -->
        <div class="mb-3 flex items-baseline justify-between">
          <div>
            <p class="text-[10px] text-slate-400 font-medium">Akakçe En Düşük Liste Fiyatı</p>
            <div class="flex items-baseline space-x-2 mt-0.5">
              <span class="text-2xl font-black tracking-tight text-white">
                ${p.current_price_str}
              </span>
            </div>
            ${(p.avg_price && p.avg_price > 0 && isDeal) ? `
              <div class="text-[11px] text-slate-400 flex items-center space-x-1.5 mt-1">
                <span>Piyasa Ort.: <span class="line-through text-slate-500 font-medium">${p.avg_price_str}</span></span>
                <span class="text-emerald-400 font-black">(-%${dealPct} Fırsat)</span>
              </div>
            ` : ''}
          </div>
          <div class="text-right">
            ${diffBadge}
          </div>
        </div>

        <!-- Akakçe En Ucuz 3 Satıcı Vitrini -->
        <div class="space-y-1.5 mb-3 bg-slate-950/40 p-2.5 rounded-xl border border-slate-800/80">
          <div class="flex items-center justify-between pb-1.5 mb-1 border-b border-slate-800/80">
            <span class="text-[11px] font-bold text-slate-300 flex items-center space-x-1.5">
              <i data-lucide="award" class="w-3.5 h-3.5 text-amber-400"></i>
              <span>Akakçe En Ucuz 3 Satıcı</span>
            </span>
            <span class="text-[10px] text-slate-500">Dün: ${p.yesterday_price_str}</span>
          </div>
          ${topSellersHtml}
        </div>
      </div>

      <!-- Alt Kısım: Alarm Eşiği ve Aksiyonlar -->
      <div class="pt-3 border-t border-slate-800/80 space-y-2.5">
        <!-- Eşik Bilgisi -->
        <div class="flex items-center justify-between bg-slate-800/20 px-3 py-1.5 rounded-xl border border-slate-800/50">
          <div class="flex items-center space-x-1.5">
            <i data-lucide="target" class="w-3.5 h-3.5 text-amber-400"></i>
            <span class="text-xs text-slate-300">Hedef Eşik:</span>
            <span class="text-xs font-bold text-amber-300">${thresholdFormatted}</span>
          </div>
          <button onclick="openThresholdModal('${p.id}', '${p.name} ${p.capacity}', ${p.threshold_price})" class="text-[11px] text-slate-400 hover:text-emerald-400 font-medium transition">
            Değiştir
          </button>
        </div>

        <!-- Butonlar -->
        <div class="grid grid-cols-2 gap-2">
          <button onclick="handlePriceGraphClick('${p.id}')" class="inline-flex items-center justify-center space-x-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 px-3 rounded-xl transition shadow-md shadow-blue-600/20">
            <i data-lucide="line-chart" class="w-3.5 h-3.5"></i>
            <span>📊 Fiyat Grafiği</span>
          </button>
          <a href="${p.direct_link}" target="_blank" class="inline-flex items-center justify-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2 px-3 rounded-xl transition shadow-md shadow-emerald-600/10">
            <i data-lucide="shopping-cart" class="w-3.5 h-3.5"></i>
            <span>En Ucuza Git</span>
          </a>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  lucide.createIcons();
}

// Ortak Tarih ve Formatlama Yardımcıları
const TR_MONTH_NAMES = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'
];

function parseDateAny(dateStr) {
  if (!dateStr) return new Date();
  if (dateStr.includes('-')) {
    const p = dateStr.split('-');
    return new Date(parseInt(p[0]), parseInt(p[1]) - 1, parseInt(p[2]));
  }
  if (dateStr.includes('.')) {
    const p = dateStr.split('.');
    return new Date(parseInt(p[2]), parseInt(p[1]) - 1, parseInt(p[0]));
  }
  return new Date(dateStr);
}

function formatTurkishAxisDate(dateStr) {
  const d = parseDateAny(dateStr);
  return `${d.getDate()} ${TR_MONTH_NAMES[d.getMonth()]}`;
}

function formatTurkishTooltipDate(dateStr, priceVal) {
  const d = parseDateAny(dateStr);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  const formattedPrice = (typeof priceVal === 'number' ? priceVal : parseFloat(priceVal) || 0)
    .toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${dd}.${mm}.${yyyy} - ${formattedPrice} TL`;
}

// 3. Fiyat Grafiği & Akakçe Değişim Analizi
let currentMainPeriod = '1yil'; // '1yil', '6ay', '1ay'
let currentChartMode = '1year'; // Geriye uyumluluk için
let cachedHistoryData = null;

function switchMainChartPeriod(period) {
  currentMainPeriod = period;
  currentChartMode = '1year';
  
  const p1y = document.getElementById('chartPeriod1yBtn');
  const p6m = document.getElementById('chartPeriod6mBtn');
  const p1m = document.getElementById('chartPeriod1mBtn');
  
  [p1y, p6m, p1m].forEach(b => {
    if (b) b.className = 'px-3 py-1 rounded-lg font-medium text-slate-400 hover:text-slate-200 transition';
  });
  
  const activeBtn = period === '1yil' ? p1y : (period === '6ay' ? p6m : p1m);
  if (activeBtn) {
    activeBtn.className = 'px-3 py-1 rounded-lg font-semibold bg-emerald-600 text-white shadow transition';
  }
  
  renderChartWithCurrentData();
}

function switchChartMode(mode) {
  switchMainChartPeriod(mode === 'live' ? '1ay' : '1yil');
}

function changeChartProduct(productId) {
  loadProductChart(productId);
}

async function handlePriceGraphClick(productId) {
  // 1. Ana sayfadaki "Fiyat Değişim Analizi & Geçmiş Grafiği" alanını güncelle
  const chartSelect = document.getElementById('chartProductSelect');
  if (chartSelect) chartSelect.value = productId;
  await loadProductChart(productId, false);

  // 2. Pop-up Fiyat Değişim Grafiği modalını aç
  await openAkakceAnalysisModal(productId);
}

async function selectProductForChart(productId) {
  document.getElementById('chartProductSelect').value = productId;
  await loadProductChart(productId);
  const container = document.getElementById('stats1yContainer');
  if (container) {
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

async function loadProductChart(productId, showLoading = true) {
  currentChartProductId = productId;
  const chartSelect = document.getElementById('chartProductSelect');
  if (chartSelect && chartSelect.value !== productId) {
    chartSelect.value = productId;
  }
  try {
    const res = await fetch(`/api/history/${productId}?limit=100`);
    cachedHistoryData = await res.json();
    
    update1YearStatCards(cachedHistoryData);
    renderChartWithCurrentData();
  } catch (err) {
    console.error('Grafik yüklenirken hata:', err);
  }
}

function update1YearStatCards(data) {
  if (!data) return;
  const stats = data.stats_1y || {};
  const thresholdVal = data.threshold_price || 0;
  
  // 1. En Düşük Fiyat
  const minP = stats.min_price;
  const minEl = document.getElementById('stat1yMinPrice');
  const minDateEl = document.getElementById('stat1yMinDate');
  const riseEl = document.getElementById('stat1yRise');
  
  if (minP) {
    minEl.innerText = `${minP.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL`;
    minDateEl.innerText = `En Düşük: ${stats.min_date || '-'}`;
    riseEl.innerText = stats.rise_from_min_tl > 0 
      ? `🚀 Dip fiyattan +${stats.rise_from_min_tl.toLocaleString('tr-TR')} TL (%${stats.rise_from_min_pct}) yükseldi`
      : `En düşük fiyatta!`;
  } else {
    minEl.innerText = '-';
    minDateEl.innerText = 'Veri yok';
    riseEl.innerText = '-';
  }
  
  // 2. En Yüksek Fiyat
  const maxP = stats.max_price;
  const maxEl = document.getElementById('stat1yMaxPrice');
  const maxDateEl = document.getElementById('stat1yMaxDate');
  const dropEl = document.getElementById('stat1yDrop');
  
  if (maxP) {
    maxEl.innerText = `${maxP.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL`;
    maxDateEl.innerText = `Zirve: ${stats.max_date || '-'}`;
    dropEl.innerText = stats.drop_from_max_tl > 0
      ? `📉 Zirve fiyattan -${stats.drop_from_max_tl.toLocaleString('tr-TR')} TL (%${stats.drop_from_max_pct}) düştü`
      : `Zirve seviyesinde!`;
  } else {
    maxEl.innerText = '-';
    maxDateEl.innerText = 'Veri yok';
    dropEl.innerText = '-';
  }
  
  // 3. Ortalama Fiyat & İndirim Oranı
  const netEl = document.getElementById('stat1yNetChange');
  const oldestDateEl = document.getElementById('stat1yOldestDate');
  const netNoteEl = document.getElementById('stat1yNetNote');
  
  if (stats.avg_price) {
    const avgFormatted = `${stats.avg_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL`;
    const dropPct = stats.drop_from_avg_pct || 0;
    if (dropPct >= 20) {
      netEl.innerText = avgFormatted;
      netEl.className = 'text-lg font-bold text-amber-300';
      oldestDateEl.innerText = `Piyasa Ortalaması`;
      netNoteEl.innerHTML = `<span class="text-amber-400 font-black">🔥 %${dropPct} İndirim Fırsatı</span>`;
    } else if (stats.oldest_price) {
      const netTL = stats.net_1y_change_tl || 0;
      const netPct = stats.net_1y_change_pct || 0;
      const isUp = netTL >= 0;
      netEl.innerText = `${isUp ? '+' : ''}${netTL.toLocaleString('tr-TR')} TL (%${netPct})`;
      netEl.className = `text-lg font-bold ${isUp ? 'text-rose-400' : 'text-emerald-400'}`;
      oldestDateEl.innerText = `Ortalama: ${avgFormatted}`;
      netNoteEl.innerText = isUp ? 'Piyasa genelinde fiyat arttı' : 'Piyasa genelinde fiyat düştü';
    } else {
      netEl.innerText = avgFormatted;
      oldestDateEl.innerText = 'Piyasa Ortalaması';
      netNoteEl.innerText = 'Akakçe Fiyat Seviyesi';
    }
  } else if (stats.oldest_price) {
    const netTL = stats.net_1y_change_tl || 0;
    const netPct = stats.net_1y_change_pct || 0;
    const isUp = netTL >= 0;
    netEl.innerText = `${isUp ? '+' : ''}${netTL.toLocaleString('tr-TR')} TL (%${netPct})`;
    netEl.className = `text-lg font-bold ${isUp ? 'text-rose-400' : 'text-emerald-400'}`;
    oldestDateEl.innerText = `1 Yıl Önce: ${stats.oldest_price.toLocaleString('tr-TR')} TL (${stats.oldest_date})`;
    netNoteEl.innerText = isUp ? 'Piyasa genelinde fiyat arttı' : 'Piyasa genelinde fiyat düştü';
  } else {
    netEl.innerText = '-';
    oldestDateEl.innerText = 'Geçmiş veri bekleniyor';
  }
  
  // 4. Hedef Alarm Eşiği
  const thrEl = document.getElementById('stat1yThreshold');
  const thrStatusEl = document.getElementById('stat1yThresholdStatus');
  
  if (thresholdVal > 0) {
    thrEl.innerText = `${thresholdVal.toLocaleString('tr-TR')} TL`;
    const curP = (cachedHistoryData.live_history && cachedHistoryData.live_history.length > 0)
      ? cachedHistoryData.live_history[cachedHistoryData.live_history.length - 1].price
      : (cachedHistoryData.historical_1y_points && cachedHistoryData.historical_1y_points.length > 0 
          ? cachedHistoryData.historical_1y_points[cachedHistoryData.historical_1y_points.length - 1].price : 0);
          
    if (curP > 0) {
      if (curP <= thresholdVal) {
        thrStatusEl.innerText = `🚨 Hedefin altında! Alış zamanı`;
        thrStatusEl.className = 'text-[11px] font-bold text-rose-400 pt-1 border-t border-slate-800/80';
      } else {
        const diff = curP - thresholdVal;
        thrStatusEl.innerText = `Eşiğe ${diff.toLocaleString('tr-TR')} TL kaldı`;
        thrStatusEl.className = 'text-[11px] text-amber-300/90 pt-1 border-t border-slate-800/80';
      }
    }
  } else {
    thrEl.innerText = 'Tanımlanmadı';
    thrStatusEl.innerText = 'Alarm kurmak için eşik girin';
  }
}

function renderChartWithCurrentData() {
  if (!cachedHistoryData) return;
  
  const ctx = document.getElementById('priceChart').getContext('2d');
  const thresholdVal = cachedHistoryData.threshold_price || 0;
  const prodName = `${cachedHistoryData.product_name} (${cachedHistoryData.capacity || 'Standart'})`;
  
  let labels = [];
  let rawDates = [];
  let prices = [];
  let chartTitle = '';
  
  let allPoints = (cachedHistoryData.historical_1y_points && cachedHistoryData.historical_1y_points.length > 0)
    ? cachedHistoryData.historical_1y_points
    : [];

  if (allPoints.length > 0) {
    const sortedPoints = [...allPoints].sort((a, b) => parseDateAny(a.date) - parseDateAny(b.date));
    const latestDate = parseDateAny(sortedPoints[sortedPoints.length - 1].date);
    
    let filtered = [];
    let periodName = 'Son 1 Yıllık';
    
    if (currentMainPeriod === '1yil') {
      periodName = 'Son 1 Yıllık';
      filtered = sortedPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 365 * 86400000);
    } else if (currentMainPeriod === '6ay') {
      periodName = 'Son 6 Aylık';
      filtered = sortedPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 180 * 86400000);
    } else if (currentMainPeriod === '1ay') {
      periodName = 'Son 1 Aylık';
      filtered = sortedPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 30 * 86400000);
    }
    
    if (filtered.length < 3) {
      filtered = sortedPoints.slice(-Math.min(sortedPoints.length, currentMainPeriod === '1ay' ? 5 : 10));
    }
    
    rawDates = filtered.map(p => p.date);
    labels = rawDates.map(d => formatTurkishAxisDate(d));
    prices = filtered.map(p => p.price);
    chartTitle = `${prodName} - Akakçe ${periodName} Fiyat Değişim Grafiği (${prices.length} Değişim Noktası)`;
  } else {
    const live = cachedHistoryData.live_history || [];
    rawDates = live.map(h => h.checked_at ? h.checked_at.split(' ')[0] : 'Bugün');
    labels = live.map(h => {
      if (!h.checked_at) return '';
      const parts = h.checked_at.split(' ');
      const dateParts = parts[0].split('-');
      const timeParts = parts[1].split(':');
      return `${dateParts[2]}.${dateParts[1]} ${timeParts[0]}:${timeParts[1]}`;
    });
    prices = live.map(h => h.price);
    chartTitle = `${prodName} - Takip Kayıtları (${prices.length} Kontrol)`;
  }
  
  const subEl = document.getElementById('chartSubtitle');
  if (subEl) subEl.innerText = chartTitle;
  
  const thresholdLine = prices.map(() => (thresholdVal > 0 ? thresholdVal : null));
  
  const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
  const maxPrice = prices.length > 0 ? Math.max(...prices) : 0;
  
  const pointColors = prices.map(p => {
    if (p === minPrice) return '#10b981';
    if (p === maxPrice) return '#f43f5e';
    return '#38bdf8';
  });
  
  const pointRadii = prices.map(p => {
    if (p === minPrice || p === maxPrice) return 6;
    return prices.length > 40 ? 2.5 : 4;
  });

  if (priceChart) {
    priceChart.destroy();
  }

  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      rawDates: rawDates,
      datasets: [
        {
          label: 'En Düşük Liste Fiyatı (TL)',
          data: prices,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.08)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.25,
          pointBackgroundColor: pointColors,
          pointBorderColor: '#0f172a',
          pointBorderWidth: 1.5,
          pointRadius: pointRadii,
          pointHoverRadius: 7
        },
        ...(thresholdVal > 0 ? [{
          label: `Alarm Eşiği (${thresholdVal.toLocaleString('tr-TR')} TL)`,
          data: thresholdLine,
          borderColor: '#f43f5e',
          borderWidth: 2,
          borderDash: [6, 6],
          fill: false,
          pointRadius: 0
        }] : [])
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          labels: { color: '#cbd5e1', font: { size: 11 } }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#e2e8f0',
          bodyColor: '#38bdf8',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            title: function() { return ''; },
            label: function(ctx) {
              const val = ctx.raw;
              if (!val) return '';
              let extra = '';
              if (val === minPrice) extra = ' 🟢 (Dönem İçi En Düşük)';
              if (val === maxPrice) extra = ' 🔴 (Dönem İçi En Yüksek)';
              const rDate = ctx.chart.data.rawDates ? ctx.chart.data.rawDates[ctx.dataIndex] : ctx.label;
              return `${formatTurkishTooltipDate(rDate, val)}${extra}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(51, 65, 85, 0.2)' },
          ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 45, autoSkip: true, maxTicksLimit: 20 }
        },
        y: {
          grid: { color: 'rgba(51, 65, 85, 0.2)' },
          ticks: {
            color: '#94a3b8',
            font: { size: 10 },
            callback: val => `${val.toLocaleString('tr-TR')} TL`
          }
        }
      }
    }
  });
}

// 4. Günlük 10:00 Raporları Sekmesi
async function loadReports() {
  try {
    const res = await fetch('/api/reports');
    const reports = await res.json();
    const list = document.getElementById('reportsList');
    
    if (!reports || reports.length === 0) {
      list.innerHTML = `
        <div class="py-10 text-center text-slate-500 text-xs">
          Henüz oluşturulmuş bir 10:00 günlük raporu bulunmuyor.<br>
          Üst menüdeki "10:00 Raporu Simüle Et" butonuna basarak ilk raporunuzu hemen üretebilirsiniz.
        </div>`;
      return;
    }

    list.innerHTML = '';
    reports.forEach(r => {
      const isDown = r.price_diff < 0;
      const isUp = r.price_diff > 0;
      
      const item = document.createElement('div');
      item.className = 'py-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs';
      item.innerHTML = `
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-slate-200 text-sm">${r.product_name || 'Samsung 990 EVO Plus'} (${r.product_capacity || ''})</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400">${r.report_date}</span>
          </div>
          <p class="text-slate-400">${r.summary_text.replace(/•/g, '').trim()}</p>
          ${r.campaign_notes ? `
            <div class="text-[11px] text-emerald-400 font-medium mt-1">
              ${r.campaign_notes.replace(/\n/g, ' | ')}
            </div>
          ` : ''}
        </div>
        <div class="flex items-center space-x-4 shrink-0">
          <div class="text-right">
            <p class="text-slate-400 text-[11px]">En Ucuz Satıcı</p>
            <p class="font-bold text-slate-200">${r.current_seller}</p>
          </div>
          <div class="text-right">
            <p class="text-slate-400 text-[11px]">Rapor Fiyatı</p>
            <p class="text-sm font-black ${isDown ? 'text-emerald-400' : isUp ? 'text-rose-400' : 'text-slate-200'}">
              ${r.current_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
            </p>
          </div>
        </div>
      `;
      list.appendChild(item);
    });
  } catch (err) {
    console.error('Raporlar yüklenemedi:', err);
  }
}

// 5. Alarmlar Sekmesi
async function loadAlarms() {
  try {
    const res = await fetch('/api/alarms');
    const alarms = await res.json();
    const list = document.getElementById('alarmsList');
    
    if (!alarms || alarms.length === 0) {
      list.innerHTML = `
        <div class="py-10 text-center text-slate-500 text-xs">
          Henüz eşik altına düşen alarm tetiklenmesi gerçekleşmedi.<br>
          Fiyat belirlediğiniz eşiğin altına indiğinde burada ayrıntılı kayıtlar listelenecektir.
        </div>`;
      return;
    }

    list.innerHTML = '';
    alarms.forEach(a => {
      const item = document.createElement('div');
      item.className = 'py-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs';
      item.innerHTML = `
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-500/20 text-rose-400 border border-rose-500/30">
              🚨 EŞİK ALTI ALARM
            </span>
            <span class="font-bold text-slate-200 text-sm">${a.product_name || 'Ürün'} (${a.product_capacity || ''})</span>
            <span class="text-slate-500 text-[11px]">${a.triggered_at}</span>
          </div>
          <p class="text-slate-400">
            Hedeflenen Eşik: <b class="text-amber-300">${a.threshold_price.toLocaleString('tr-TR')} TL</b> ➔ 
            Yakalanan Fiyat: <b class="text-emerald-400">${a.trigger_price.toLocaleString('tr-TR')} TL</b>
          </p>
        </div>
        <div class="flex items-center space-x-3">
          <span class="text-slate-300 font-semibold">${a.seller}</span>
          ${a.direct_link ? `
            <a href="${a.direct_link}" target="_blank" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center space-x-1">
              <i data-lucide="external-link" class="w-3 h-3"></i>
              <span>Satıcıya Git</span>
            </a>
          ` : ''}
        </div>
      `;
      list.appendChild(item);
    });
    lucide.createIcons();
  } catch (err) {
    console.error('Alarmlar yüklenemedi:', err);
  }
}

// Sekme Geçişi
function switchTab(tab) {
  activeTab = tab;
  const reportsBtn = document.getElementById('tabReportsBtn');
  const alarmsBtn = document.getElementById('tabAlarmsBtn');
  const reportsContent = document.getElementById('tabReportsContent');
  const alarmsContent = document.getElementById('tabAlarmsContent');

  if (tab === 'reports') {
    reportsBtn.className = 'px-4 py-2.5 font-semibold text-sm border-b-2 border-emerald-500 text-emerald-400 flex items-center space-x-2';
    alarmsBtn.className = 'px-4 py-2.5 font-semibold text-sm border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2';
    reportsContent.classList.remove('hidden');
    alarmsContent.classList.add('hidden');
    loadReports();
  } else {
    alarmsBtn.className = 'px-4 py-2.5 font-semibold text-sm border-b-2 border-emerald-500 text-emerald-400 flex items-center space-x-2';
    reportsBtn.className = 'px-4 py-2.5 font-semibold text-sm border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2';
    alarmsContent.classList.remove('hidden');
    reportsContent.classList.add('hidden');
    loadAlarms();
  }
  lucide.createIcons();
}

// 6. Anlık Kontrol Butonu
async function triggerCheckNow() {
  const icon = document.getElementById('checkIcon');
  icon.classList.add('animate-spin');
  showToast('Akakçe canlı fiyat taraması başlatıldı...', 'info');

  try {
    const res = await fetch('/api/check-now', { method: 'POST' });
    const data = await res.json();
    
    await loadProducts(false);
    await loadStatus();
    if (currentChartProductId) await loadProductChart(currentChartProductId, false);
    
    showToast('Tüm fiyatlar Akakçe üzerinden güncellendi!', 'success');
  } catch (err) {
    showToast('Fiyat taraması sırasında hata oluştu.', 'error');
  } finally {
    icon.classList.remove('animate-spin');
  }
}

// 7. Günlük 10:00 Raporu Simülasyonu
async function triggerDailyReportSim() {
  showToast('Saat 10:00 Günlük Raporu hazırlanıyor...', 'info');
  try {
    const res = await fetch('/api/generate-daily-report', { method: 'POST' });
    const data = await res.json();
    
    await loadProducts(false);
    await loadReports();
    switchTab('reports');
    showToast('Saat 10:00 Günlük Fiyat Raporu başarıyla oluşturuldu ve kaydedildi!', 'success');
  } catch (err) {
    showToast('Rapor oluşturulurken hata meydana geldi.', 'error');
  }
}

// 8. Eşik Modalı
function openThresholdModal(productId, productName, currentThreshold) {
  document.getElementById('modalProductId').value = productId;
  document.getElementById('modalProductName').value = productName;
  document.getElementById('modalThresholdInput').value = currentThreshold || '';
  document.getElementById('thresholdModal').classList.remove('hidden');
}

function closeThresholdModal() {
  document.getElementById('thresholdModal').classList.add('hidden');
}

async function saveThresholdModal() {
  const prodId = document.getElementById('modalProductId').value;
  const val = parseFloat(document.getElementById('modalThresholdInput').value) || 0.0;

  try {
    const res = await fetch(`/api/products/${prodId}/threshold`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ threshold_price: val })
    });
    
    if (res.ok) {
      showToast('Fiyat eşiği başarıyla güncellendi!', 'success');
      closeThresholdModal();
      await loadProducts(false);
      if (currentChartProductId === prodId) await loadProductChart(prodId, false);
    } else {
      showToast('Eşik güncellenemedi.', 'error');
    }
  } catch (err) {
    showToast('Hata oluştu.', 'error');
  }
}

// 9. Ayarlar Modalı
async function openSettingsModal() {
  try {
    const res = await fetch('/api/settings');
    const s = await res.json();

    document.getElementById('settingDailyTime').value = s.daily_report_time || '10:00';
    document.getElementById('settingInterval').value = s.check_interval_minutes || 60;
    document.getElementById('settingDesktopNotif').checked = s.desktop_enabled;
    document.getElementById('settingTelegramNotif').checked = s.telegram_enabled;
    document.getElementById('settingTelegramToken').value = s.telegram_bot_token || '';
    document.getElementById('settingTelegramChatId').value = s.telegram_chat_id || '';
    document.getElementById('settingDiscordNotif').checked = s.discord_enabled;
    document.getElementById('settingDiscordUrl').value = s.discord_webhook_url || '';

    document.getElementById('settingsModal').classList.remove('hidden');
    lucide.createIcons();
  } catch (err) {
    showToast('Ayarlar yüklenemedi.', 'error');
  }
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.add('hidden');
}

async function saveSettingsModal() {
  const payload = {
    daily_report_time: document.getElementById('settingDailyTime').value.trim() || '10:00',
    check_interval_minutes: parseInt(document.getElementById('settingInterval').value) || 60,
    scheduler_enabled: true,
    desktop_enabled: document.getElementById('settingDesktopNotif').checked,
    telegram_enabled: document.getElementById('settingTelegramNotif').checked,
    telegram_bot_token: document.getElementById('settingTelegramToken').value.trim(),
    telegram_chat_id: document.getElementById('settingTelegramChatId').value.trim(),
    discord_enabled: document.getElementById('settingDiscordNotif').checked,
    discord_webhook_url: document.getElementById('settingDiscordUrl').value.trim()
  };

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast('Ayarlar başarıyla kaydedildi ve zamanlayıcı güncellendi.', 'success');
      closeSettingsModal();
      await loadStatus();
    } else {
      showToast('Ayarlar kaydedilemedi.', 'error');
    }
  } catch (err) {
    showToast('Hata oluştu.', 'error');
  }
}

async function testNotificationChannel(channel) {
  showToast(`${channel.toUpperCase()} bildirim testi gönderiliyor...`, 'info');
  try {
    const res = await fetch('/api/test-notification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel: channel })
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showToast(data.message, 'success');
    } else {
      showToast(data.detail || data.message || 'Test başarısız.', 'error');
    }
  } catch (err) {
    showToast('Test sırasında hata meydana geldi.', 'error');
  }
}

// 10. Yeni Ürün Modalı
function openAddProductModal() {
  document.getElementById('addProductModal').classList.remove('hidden');
}

function closeAddProductModal() {
  document.getElementById('addProductModal').classList.add('hidden');
}

async function submitNewProduct() {
  const name = document.getElementById('newProdName').value.trim();
  const category = document.getElementById('newProdCategory')?.value || 'SSD & Depolama';
  const cap = document.getElementById('newProdCap').value.trim();
  const url = document.getElementById('newProdUrl').value.trim();
  const thr = parseFloat(document.getElementById('newProdThreshold').value) || 0.0;

  if (!name || !url) {
    showToast('Lütfen en azından Ürün Adı ve Akakçe URL girin.', 'error');
    return;
  }

  showToast('Ürün ekleniyor ve ilk fiyat çekiliyor...', 'info');
  try {
    const res = await fetch('/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, category, capacity: cap, url, threshold_price: thr })
    });
    if (res.ok) {
      showToast('Yeni ürün eklendi ve listeye alındı!', 'success');
      closeAddProductModal();
      await loadProducts(true);
      await loadStatus();
    } else {
      showToast('Ürün eklenemedi.', 'error');
    }
  } catch (err) {
    showToast('Hata oluştu.', 'error');
  }
}

// 11. Toast Bildirim Kutusu
let toastTimeout = null;
function showToast(msg, type = 'success') {
  const box = document.getElementById('toastBox');
  const inner = document.getElementById('toastInner');
  const txt = document.getElementById('toastMsg');
  const icon = document.getElementById('toastIcon');

  txt.innerText = msg;

  if (type === 'error') {
    inner.className = 'bg-rose-950/90 border border-rose-500 shadow-2xl rounded-xl p-4 flex items-center space-x-3 text-xs text-rose-100 max-w-md';
    icon.setAttribute('data-lucide', 'alert-circle');
    icon.className = 'w-5 h-5 text-rose-400 shrink-0';
  } else if (type === 'info') {
    inner.className = 'bg-slate-900 border border-cyan-500/50 shadow-2xl rounded-xl p-4 flex items-center space-x-3 text-xs text-cyan-100 max-w-md';
    icon.setAttribute('data-lucide', 'info');
    icon.className = 'w-5 h-5 text-cyan-400 shrink-0';
  } else {
    inner.className = 'bg-slate-900 border border-emerald-500/50 shadow-2xl rounded-xl p-4 flex items-center space-x-3 text-xs text-slate-100 max-w-md';
    icon.setAttribute('data-lucide', 'check-circle');
    icon.className = 'w-5 h-5 text-emerald-400 shrink-0';
  }

  lucide.createIcons();

  box.classList.remove('translate-y-24', 'opacity-0', 'pointer-events-none');
  
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    box.classList.add('translate-y-24', 'opacity-0', 'pointer-events-none');
  }, 4000);
}

// =========================================================================
// 12. Birebir Akakçe Fiyat Analizi Modalı (Görseldeki Pop-up Tasarımı)
// =========================================================================
let akakceModalChartInstance = null;
let modalProductData = null;
let modalSelectedPeriod = '6ay';

async function openAkakceAnalysisModal(productId) {
  showToast('Fiyat analizi verileri açılıyor...', 'info');
  
  try {
    const res = await fetch(`/api/history/${productId}?limit=120`);
    if (!res.ok) throw new Error('Veri çekilemedi');
    modalProductData = await res.json();
    
    // Modalı aç
    document.getElementById('akakceAnalysisModal').classList.remove('hidden');
    lucide.createIcons();
    
    // Kullanıcının görselinde varsayılan 6 Ay seçili
    setModalAnalysisPeriod('6ay');
  } catch (err) {
    console.error('Modal açılırken hata:', err);
    showToast('Fiyat analizi verisi yüklenirken hata oluştu.', 'error');
  }
}

function closeAkakceAnalysisModal() {
  const modal = document.getElementById('akakceAnalysisModal');
  if (modal) modal.classList.add('hidden');
  if (akakceModalChartInstance) {
    akakceModalChartInstance.destroy();
    akakceModalChartInstance = null;
  }
}

// =========================================================================
// 11.5. Büyük Boy Görsel İnceleme Modalı (Lightbox)
// =========================================================================
function openProductImageModal(productId) {
  const p = allProductsList.find(x => x.id === productId);
  if (!p) return;
  
  const modal = document.getElementById('imageLightboxModal');
  const titleEl = document.getElementById('lightboxProductTitle');
  const imgEl = document.getElementById('lightboxImage');
  const priceEl = document.getElementById('lightboxPrice');
  const linkEl = document.getElementById('lightboxDirectLink');
  
  if (titleEl) titleEl.innerText = `${p.name} (${p.capacity || 'Standart'})`;
  if (priceEl) priceEl.innerText = p.current_price_str || '-';
  if (linkEl) linkEl.href = p.direct_link || p.url || '#';
  
  const localImg = `/static/product_imgs/${p.id}.jpg`;
  const remoteImg = p.image_url || '/static/logo.png';
  
  if (imgEl) {
    imgEl.src = localImg;
    imgEl.onerror = () => {
      imgEl.onerror = null;
      imgEl.src = remoteImg;
    };
  }
  
  if (modal) {
    modal.classList.remove('hidden');
    lucide.createIcons();
  }
}

function closeImageLightbox() {
  const modal = document.getElementById('imageLightboxModal');
  if (modal) modal.classList.add('hidden');
}

const lbBg = document.getElementById('imageLightboxModal');
if (lbBg) {
  lbBg.addEventListener('click', (e) => {
    if (e.target === lbBg) {
      closeImageLightbox();
    }
  });
}

// Modal dışına tıklandığında veya ESC basıldığında kapatma
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeImageLightbox();
    closeAkakceAnalysisModal();
    closeAddProductModal();
    closeSettingsModal();
    closeThresholdModal();
  }
});

const modalBg = document.getElementById('akakceAnalysisModal');
if (modalBg) {
  modalBg.addEventListener('click', (e) => {
    if (e.target === modalBg) {
      closeAkakceAnalysisModal();
    }
  });
}

function setModalAnalysisPeriod(period) {
  if (!modalProductData) return;
  modalSelectedPeriod = period;
  
  // 1. Buton Aktiflik Stillerini Güncelle
  const btnIds = {
    '1yil': 'btnPeriod1y',
    '6ay': 'btnPeriod6m',
    '1ay': 'btnPeriod1m',
    '1hafta': 'btnPeriod1w',
    'tahmin': 'btnPeriodEst'
  };

  Object.entries(btnIds).forEach(([pKey, id]) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    if (pKey === period) {
      btn.className = 'px-5 py-1.5 sm:py-2 text-xs sm:text-sm rounded-xl border-2 border-slate-500 bg-slate-100 text-slate-900 font-bold shadow-sm transition';
    } else {
      btn.className = 'px-5 py-1.5 sm:py-2 text-xs sm:text-sm rounded-xl border border-slate-200 text-slate-600 font-medium hover:border-slate-300 hover:bg-slate-50 transition';
    }
  });

  // 2. Üst Başlık: "[Ürün Tam Adı] son 6 aylık fiyat değişim grafiği"
  const fullName = `${modalProductData.product_name} ${modalProductData.capacity || ''}`.trim();
  const periodTextMap = {
    '1yil': 'son 1 yıllık',
    '6ay': 'son 6 aylık',
    '1ay': 'son 1 aylık',
    '1hafta': 'son 1 haftalık',
    'tahmin': 'gelecek 15 günlük tahmini'
  };
  const periodText = periodTextMap[period] || 'son 6 aylık';
  const titleEl = document.getElementById('modalAnalysisTitle');
  if (titleEl) {
    titleEl.innerText = `${fullName} ${periodText} fiyat değişim grafiği`;
  }
  const subEl = document.getElementById('modalAnalysisSubtitle');
  if (subEl) {
    subEl.innerText = `${fullName} ${periodText} fiyat değişim grafiği`;
  }

  // 3. Veri Noktalarını Filtrele
  let rawPoints = [];
  if (modalProductData.historical_1y_points && modalProductData.historical_1y_points.length > 0) {
    rawPoints = modalProductData.historical_1y_points.map(p => ({
      date: p.date,
      display_date: p.display_date || p.date,
      price: p.price
    }));
  } else if (modalProductData.live_history && modalProductData.live_history.length > 0) {
    rawPoints = modalProductData.live_history.map(h => {
      const parts = h.checked_at.split(' ')[0].split('-');
      return {
        date: h.checked_at.split(' ')[0],
        display_date: `${parts[2]}.${parts[1]}.${parts[0]}`,
        price: h.price
      };
    });
  }

  if (rawPoints.length === 0) {
    document.getElementById('modalRowMaxPrice').innerText = '-';
    document.getElementById('modalRowMinPrice').innerText = '-';
    document.getElementById('modalRowCurrentPrice').innerText = '-';
    document.getElementById('modalStatusPill').innerText = 'Bu ürün için henüz geçmiş fiyat kaydı bulunmuyor.';
    return;
  }

  // En son tarihi referans al
  const latestDate = parseDateAny(rawPoints[rawPoints.length - 1].date);
  let filteredPoints = [];

  if (period === '1yil') {
    filteredPoints = rawPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 365 * 86400000);
  } else if (period === '6ay') {
    filteredPoints = rawPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 180 * 86400000);
  } else if (period === '1ay') {
    filteredPoints = rawPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 30 * 86400000);
  } else if (period === '1hafta') {
    filteredPoints = rawPoints.filter(p => (latestDate - parseDateAny(p.date)) <= 7 * 86400000);
  } else if (period === 'tahmin') {
    filteredPoints = rawPoints.slice(-15);
  }

  if (filteredPoints.length < 2) {
    filteredPoints = rawPoints.slice(-Math.min(rawPoints.length, 3));
  }

  let prices = filteredPoints.map(p => p.price);
  let rawDates = filteredPoints.map(p => p.date);
  let labels = filteredPoints.map(p => formatTurkishAxisDate(p.date));

  // Gelecek 15 gün tahmini modunda ek projeksiyon noktaları ekle
  let isTahminMode = (period === 'tahmin');
  let projectedLabels = [...labels];
  let projectedPrices = [...prices];
  let projectedRawDates = [...rawDates];

  if (isTahminMode) {
    const curP = prices[prices.length - 1];
    const curD = parseDateAny(rawDates[rawDates.length - 1]);
    const steps = [3, 7, 11, 15];
    steps.forEach(offsetDays => {
      const futureD = new Date(curD.getTime() + offsetDays * 86400000);
      const isoD = `${futureD.getFullYear()}-${String(futureD.getMonth() + 1).padStart(2, '0')}-${String(futureD.getDate()).padStart(2, '0')}`;
      projectedRawDates.push(isoD);
      projectedLabels.push(formatTurkishAxisDate(isoD));
      projectedPrices.push(curP);
    });
  }

  // 4. Dönem İçi En Yüksek, En Düşük ve Şu Andaki Fiyat
  const periodMin = Math.min(...prices);
  const periodMax = Math.max(...prices);
  const currentPrice = prices[prices.length - 1];

  const formatTL = (v) => v.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' TL';
  document.getElementById('modalRowMaxPrice').innerText = formatTL(periodMax);
  document.getElementById('modalRowMinPrice').innerText = formatTL(periodMin);
  document.getElementById('modalRowCurrentPrice').innerText = formatTL(currentPrice);

  // 5. Durum İkaz Kutusu (Görseldeki Birebir Mantık)
  const pill = document.getElementById('modalStatusPill');
  const periodDurationName = {
    '1yil': 'son 1 yılın',
    '6ay': 'son 6 ayın',
    '1ay': 'son 1 ayın',
    '1hafta': 'son 1 haftanın',
    'tahmin': 'bu dönemin'
  };
  const durationLabel = periodDurationName[period] || 'son 6 ayın';

  if (Math.abs(currentPrice - periodMax) < 0.05) {
    pill.innerText = `Şu andaki fiyat ${durationLabel} en yüksek fiyatı.`;
    pill.className = 'bg-slate-100 border border-slate-200/90 rounded-xl py-2.5 px-6 text-center text-xs sm:text-sm font-semibold text-slate-800 shadow-sm';
  } else if (Math.abs(currentPrice - periodMin) < 0.05) {
    pill.innerText = `Şu andaki fiyat ${durationLabel} en düşük fiyatı. En iyi alım zamanı!`;
    pill.className = 'bg-emerald-50 border border-emerald-300 rounded-xl py-2.5 px-6 text-center text-xs sm:text-sm font-bold text-emerald-800 shadow-sm';
  } else {
    const diffFromMin = (((currentPrice - periodMin) / periodMin) * 100).toFixed(1);
    const diffFromMax = (((periodMax - currentPrice) / periodMax) * 100).toFixed(1);
    pill.innerText = `Şu andaki fiyat dönem içi en düşük fiyattan %${diffFromMin} yukarıda, en yüksek fiyattan %${diffFromMax} aşağıda.`;
    pill.className = 'bg-slate-100 border border-slate-200/90 rounded-xl py-2.5 px-6 text-center text-xs sm:text-sm font-medium text-slate-700 shadow-sm';
  }

  // 6. Akakçe Çizgi Grafiği (Chart.js)
  const canvas = document.getElementById('akakceModalChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  if (akakceModalChartInstance) {
    akakceModalChartInstance.destroy();
  }

  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, 'rgba(30, 80, 180, 0.18)');
  gradient.addColorStop(1, 'rgba(30, 80, 180, 0.0)');

  const chartPrices = isTahminMode ? projectedPrices : prices;
  const chartLabels = isTahminMode ? projectedLabels : labels;
  const chartRawDates = isTahminMode ? projectedRawDates : rawDates;

  akakceModalChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: chartLabels,
      rawDates: chartRawDates,
      datasets: [
        {
          label: 'Fiyat',
          data: chartPrices,
          borderColor: '#1e50b4',
          backgroundColor: gradient,
          borderWidth: 2.5,
          borderDash: isTahminMode ? [5, 5] : [],
          fill: true,
          tension: 0.25,
          pointRadius: chartPrices.length > 35 ? 2 : 3.5,
          pointHoverRadius: 6,
          pointBackgroundColor: '#1e50b4',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#e2e8f0',
          bodyColor: '#60a5fa',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 10,
          displayColors: false,
          callbacks: {
            title: function() { return ''; },
            label: function(item) {
              const rDate = item.chart.data.rawDates ? item.chart.data.rawDates[item.dataIndex] : item.label;
              return formatTurkishTooltipDate(rDate, item.raw);
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            color: 'rgba(226, 232, 240, 0.6)',
            drawBorder: false
          },
          ticks: {
            color: '#64748b',
            font: { size: 10 },
            maxRotation: 45,
            autoSkip: true,
            maxTicksLimit: 14
          }
        },
        y: {
          grid: {
            color: 'rgba(226, 232, 240, 0.7)',
            drawBorder: false
          },
          ticks: {
            color: '#64748b',
            font: { size: 10 },
            callback: function(val) {
              return val.toLocaleString('tr-TR') + ' TL';
            }
          },
          suggestedMin: Math.floor(periodMin * 0.96),
          suggestedMax: Math.ceil(periodMax * 1.04)
        }
      }
    }
  });
}
