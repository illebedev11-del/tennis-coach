"""v53 QA: блок «Резервная копия», предпросмотр восстановления, тихое напоминание. WebKit 390, светлая и тёмная."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1])
shots = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/tennis-v53')
shots.mkdir(parents=True, exist_ok=True)
OWNER = "try{localStorage.setItem('tennis_coach_device_owner','coach_ilya')}catch(e){}"
SEED = """() => {
  store.students = [
    { id: 's1', name: 'Ваня', age: '', level: 'Средний', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() },
    { id: 's2', name: 'Маша', age: '', level: 'Средний', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() }
  ];
  store.groups = [];
  const mk = (id, notes) => normalizePlan({ id, kind: 'note', status: 'done', date: '2026-11-20', time: '18:00',
    targetType: 'student', studentId: 's1', studentName: 'Ваня', studentIds: ['s1'], groupIds: [], coaches: [{id:'coach_ilya',name:'Илья'}],
    actualStudentIds: ['s1'], goal: notes, notes, sections: emptySections(), summary: null, createdAt: nowISO(), createdBy: store.coachId });
  store.plans = [mk('a1', 'Кросс и подача'), mk('a2', 'Игра на счёт'), mk('a3', 'Работа ног')];
  setBackupMeta({ lastExportAt: new Date(Date.now() - 20 * 864e5).toISOString(), dismissedAt: '' });
  persist(); navigate('training'); render();
}"""
fails = []
def check(ok, msg):
    if not ok: fails.append(msg); print('FAIL', msg)
with sync_playwright() as p:
    b = p.webkit.launch()
    for theme in ('light', 'dark'):
        tag = theme
        c = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=theme)
        pg = c.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
        pg.add_init_script(OWNER)
        pg.goto('file://' + root + '/index.html'); pg.wait_for_timeout(400)
        pg.evaluate(SEED); pg.wait_for_timeout(400)
        # напоминание в списке
        check(pg.locator('#backup-hint').count() == 1, f'{tag}: list hint')
        check('Пора сохранить копию' in pg.locator('#backup-hint').inner_text(), f'{tag}: hint text')
        if theme == 'light':
            pg.screenshot(path=str(shots / 'v53-list-hint-light-390.png'))
        # настройки
        pg.evaluate('settings()'); pg.wait_for_timeout(700)
        card = pg.locator('#backup-row, .backup-card').first
        check(card.count() == 1 and 'РЕЗЕРВНАЯ КОПИЯ' in card.inner_text().upper(), f'{tag}: backup block')
        check('Последняя копия:' in card.inner_text(), f'{tag}: last copy date')
        check(pg.get_by_role('button', name='Сохранить копию').count() >= 1, f'{tag}: save button')
        check(pg.get_by_role('button', name='Восстановить из копии').count() == 1, f'{tag}: restore button')
        geo = pg.evaluate("""() => { const c = document.querySelector('.backup-card'); const b = [...c.querySelectorAll('.backup-actions .button')].map((x) => x.getBoundingClientRect().height);
          return { h: Math.min(...b), n: b.length, w: c.getBoundingClientRect().width, vw: innerWidth }; }""")
        check(geo['h'] >= 48 and geo['w'] <= geo['vw'] - 24, f'{tag}: button size {geo}')
        pg.screenshot(path=str(shots / f'v53-settings-{theme}-390.png'))
        # предпросмотр восстановления
        pg.evaluate("""() => {
          const copy = backupObject();
          copy.data.students.push({ id: 's_in', name: 'Новый', age: '', level: 'Средний', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() });
          openRestorePreview(copy);
        }""")
        pg.wait_for_timeout(700)
        body = pg.locator('#overlay .modal').last.inner_text()
        check('Добавить к текущим' in body and 'Заменить всё' in body, f'{tag}: restore choices {body[:200]}')
        check('ученик' in body and 'занят' in body, f'{tag}: preview counts {body[:240]}')
        pg.screenshot(path=str(shots / f'v53-restore-preview-{theme}-390.png'))
        # подтверждение замены
        pg.locator('#overlay [data-action="restore-replace"]').tap(); pg.wait_for_timeout(600)
        confirm = pg.locator('.peek-confirm')
        check(confirm.count() == 1 and 'Заменить' in confirm.inner_text(), f'{tag}: replace confirm')
        if theme == 'light':
            pg.screenshot(path=str(shots / 'v53-restore-confirm-light-390.png'))
        pg.locator('.peek-confirm [data-peek="stay"]').tap(); pg.wait_for_timeout(400)
        # merge actually adds
        before = pg.evaluate('store.students.length')
        pg.evaluate("""() => { const copy = backupObject(); copy.data.students.push({ id: 's_in2', name: 'Ещё', age: '', level: '', hand: 'right', strengths: '', weaknesses: '', priority: '', notes: [], createdAt: nowISO() }); pendingImport = copy; applyBackup(copy, 'merge'); }""")
        pg.wait_for_timeout(400)
        after = pg.evaluate('store.students.map(s => s.id)')
        check('s_in2' in after and len(after) == before + 1, f'{tag}: merge added {after}')
        check(pg.evaluate('Boolean(localStorage.getItem(storagePrefix + PREVIOUS_BACKUP))'), f'{tag}: safety copy')
        check(pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f'{tag}: no horizontal scroll')
        check(not errs, f'{tag}: page errors {errs}')
        print('done', tag); c.close()
    b.close()
print('FAILS', len(fails))
if fails: sys.exit(1)
print('PASS v53 WebKit 390 light/dark: backup block, preview, merge, safety copy')
