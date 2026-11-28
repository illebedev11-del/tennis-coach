"""v54 QA: статистика в карточке ученика. WebKit 390, светлая и тёмная."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/workspace/tennis-coach-v1/screens')
shots.mkdir(parents=True, exist_ok=True)
OWNER = "try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}"

FULL_SEED = r"""() => {
  const ilya = {id:'coach_ilya', name:'Илья'};
  const ilona = {id:'coach_ilona', name:'Илона'};
  const item = (id) => { const e = seedById[id] || {id, title:id, minutes:10}; return {id:e.id, title:e.title, minutes:e.minutes||10}; };
  const note = (n, date, coach, ids, goal) => normalizePlan({
    id: 'shot_' + n, kind:'note', status:'done', date, time:'18:00',
    studentId:'s1', studentIds:['s1'], actualStudentIds:['s1'], groupIds:[],
    coaches:[coach], goal: goal||'', notes: goal||'',
    sections:{warmup:[], main:ids.map(item), points:[], cooldown:[]}
  });
  store.students = [
    normalizeStudent({id:'s1', name:'Игорь', age:'32', level:'Средний', hand:'right', demo:true,
      priority:'Стабильность бэкхенда при повышении темпа.',
      strengths:'Стабильный форхенд, хорошее передвижение.',
      weaknesses:'Бэкхенд под давлением, вторая подача.'}),
    normalizeStudent({id:'s_empty', name:'Новый ученик', age:'16', level:'Начальный', hand:'right'}),
    normalizeStudent({id:'s_few', name:'Маша', age:'28', level:'Средний', hand:'right'})
  ];
  store.groups = [];
  store.plans = [
    note('01','2026-09-14',ilya,['gs02','se02','mv05'],'Стабильность бэкхенда, вторая подача.'),
    note('02','2026-09-21',ilona,['tr06','gs08'],'Укороченный и игра в короткий кросс.'),
    note('03','2026-09-28',ilya,['nt04','gs02','se08'],''),
    note('04','2026-10-05',ilya,['gs02','gs05','mv01'],''),
    note('05','2026-10-09',ilona,['nt01'],'Игра у сетки, удары с лёта.'),
    note('06','2026-10-14',ilya,['se02','se12','rv01'],''),
    note('07','2026-10-19',ilya,['gs02','se08','se15'],''),
    note('08','2026-10-23',ilona,['gs02','gs08','mv05'],''),
    note('09','2026-10-28',ilya,['se02','rv01','rv04'],''),
    note('10','2026-11-02',ilya,['gs02','tr02','gs05'],''),
    note('11','2026-11-07',ilona,['gs02','mv05'],''),
    note('12','2026-11-11',ilya,['se02','se12','gs04'],''),
    note('13','2026-11-16',ilya,['gs02','gs05','se08'],''),
    note('14','2026-11-20',ilona,['gs02','rv01','mv01'],''),
    note('15','2026-11-23',ilya,['gs02','se02','mv05'],'Бэкхенд под темпом и вторая подача.'),
    normalizePlan({id:'few1', kind:'note', status:'done', date:'2026-11-25', studentIds:['s_few'], actualStudentIds:['s_few'], coaches:[ilya], goal:'Кросс', notes:'Кросс', sections:{main:[{id:'gs02',title:'Кросс бэкхендом'}]}}),
    normalizePlan({id:'few2', kind:'note', status:'done', date:'2026-11-20', studentIds:['s_few'], actualStudentIds:['s_few'], coaches:[ilya], goal:'Подача', notes:'Подача', sections:{main:[{id:'se02',title:'Вторая подача с запасом над сеткой'}]}})
  ];
  persist();
}"""

fails = []
def check(ok, msg):
    if not ok:
        fails.append(msg)
        print('FAIL', msg)
    else:
        print('OK', msg)

def open_student(page, sid):
    page.evaluate(f"openStudent({sid!r})")
    page.wait_for_selector('#stats-block', timeout=8000)
    page.wait_for_timeout(450)

def capture_card(page, path):
    page.evaluate("""() => {
      const sheet = document.querySelector('.sheet');
      const modal = document.querySelector('.sheet .modal, #overlay .modal, .modal');
      [sheet, modal, document.getElementById('overlay')].forEach((n) => {
        if (!n) return;
        n.style.setProperty('transform', 'none', 'important');
        n.style.setProperty('transition', 'none', 'important');
        n.style.setProperty('max-height', 'none', 'important');
        n.style.setProperty('height', 'auto', 'important');
        n.style.setProperty('overflow', 'visible', 'important');
      });
      if (modal) modal.scrollTop = 0;
    }""")
    page.wait_for_timeout(150)
    box = page.evaluate("""() => {
      const modal = document.querySelector('.sheet .modal, #overlay .modal, .modal');
      const stats = document.getElementById('stats-block');
      const m = modal.getBoundingClientRect(), s = stats.getBoundingClientRect();
      return {mx:m.x, my:m.y, mw:m.w, mh:m.height, sy:s.y, sh:s.height, vw:innerWidth};
    }""")
    # full page then crop in a return value; also screenshot viewport tall
    page.screenshot(path=str(path), full_page=True, animations='disabled')
    return box

with sync_playwright() as p:
    browser = p.webkit.launch()
    for theme in ('light', 'dark'):
        ctx = browser.new_context(
            viewport={'width': 390, 'height': 2000},
            device_scale_factor=2, is_mobile=True, has_touch=True,
            color_scheme=theme, locale='ru-RU', timezone_id='Europe/Moscow')
        page = ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        page.add_init_script(OWNER)
        page.goto(Path(root, 'index.html').as_uri())
        page.wait_for_timeout(400)
        page.evaluate(FULL_SEED)
        page.wait_for_timeout(200)

        open_student(page, 's1')
        text = page.locator('#stats-block').inner_text()
        check('СТАТИСТИКА' in text.upper(), f'{theme}: heading')
        check('15' in text and 'занятий всего' in text, f'{theme}: total tile')
        check('за последние 30 дней' in text, f'{theme}: 30-day tile')
        check('5 дней назад' in text, f'{theme}: last session')
        check('ПО НЕДЕЛЯМ' in text.upper(), f'{theme}: weekly chart')
        check('Илья' in text and 'Илона' in text, f'{theme}: coach split')
        check('ЧАЩЕ ВСЕГО РАБОТАЛИ НАД' in text.upper(), f'{theme}: top list')
        check('Кросс бэкхендом' in text, f'{theme}: top drill')
        check('ДАВНО НЕ ПОВТОРЯЛИ' in text.upper(), f'{theme}: stale list')
        colors = page.evaluate("""() => {
          const tile = document.querySelector('.stats-tile');
          const block = document.querySelector('.stats-block');
          const t = getComputedStyle(tile).backgroundColor;
          const b = getComputedStyle(block).backgroundColor;
          return {t, b, differ: t !== b && t !== 'rgba(0, 0, 0, 0)' && t !== 'transparent'};
        }""")
        check(colors['differ'], f'{theme}: tile background distinct {colors}')
        box = capture_card(page, shots / f'v54-{theme}-390-full.png')
        check(not errs, f'{theme}: no page errors {errs}')

        page.evaluate("closeModal && closeModal('top')")
        page.wait_for_timeout(300)
        open_student(page, 's_empty')
        empty = page.locator('#stats-block').inner_text()
        check('Проведённых тренировок пока нет' in empty, f'{theme}: empty line')
        check(page.locator('#stats-block .stats-tiles').count() == 0, f'{theme}: no empty tiles')
        check('По неделям' not in empty, f'{theme}: no empty chart')

        page.evaluate("closeModal && closeModal('top')")
        page.wait_for_timeout(300)
        open_student(page, 's_few')
        few = page.locator('#stats-block').inner_text()
        check('занятий всего' in few and '2' in few, f'{theme}: few tiles')
        check('По неделям' not in few, f'{theme}: few has no chart')
        check('Чаще всего' not in few, f'{theme}: few has no top list')
        ctx.close()
    browser.close()

if fails:
    print(f'\n{len(fails)} failed')
    sys.exit(1)
print('PASS v54-mobile')
