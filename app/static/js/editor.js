/** Narzędzie “Tabela treningowa” – widoczne w plusie */
class WorkoutTableTool {
  static get toolbox() {
    return {
      title: 'Tabela treningowa',
      icon: '<svg width="17" height="17" viewBox="0 0 24 24"><path d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm0 3v3h16V8H4zm0 5v4h16v-4H4z" fill="currentColor"/></svg>'
    };
  }

  constructor({ api }) {
    this.api = api;
    this.template = {
      withHeadings: true,
      content: [
        ['Ćwiczenie', 'Powtórzenia', 'Kg'],
        ['1/2 przysiad', '10/8/6', '100/110/120 kg']
      ]
    };
  }

  render() {
    const phantom = document.createElement('div');
    phantom.style.display = 'none';
    requestAnimationFrame(() => {
      const idx = this.api.blocks.getCurrentBlockIndex();
      this.api.blocks.insert('table', this.template, {}, idx, true);
      this.api.caret.setToBlock(idx, 'end');
    });
    return phantom;
  }

  save() { return {}; }
}

// Inicjalizacja
const editor = new EditorJS({
  holder: 'editor',
  autofocus: true,
  tools: {
    paragraph: { class: Paragraph, inlineToolbar: true, config: { placeholder: 'Napisz coś…' } },
    table: { class: Table, inlineToolbar: true },
    workoutTable: { class: WorkoutTableTool }
  }
});

// Szybkie przyciski
document.getElementById('addText').onclick = () => {
  const i = editor.blocks.getBlocksCount();
  editor.blocks.insert('paragraph', { text: '' }, {}, i, true);
};
document.getElementById('addTable').onclick = () => {
  const i = editor.blocks.getBlocksCount();
  editor.blocks.insert('table', { withHeadings: true, content: [['Heading','Heading','Heading'],['','','']] }, {}, i, true);
};
document.getElementById('addWorkout').onclick = () => {
  const i = editor.blocks.getBlocksCount();
  editor.blocks.insert('table', {
    withHeadings: true,
    content: [['Ćwiczenie','Powtórzenia','Kg'],['1/2 przysiad','10/8/6','100/110/120 kg']]
  }, {}, i, true);
};

// Eksport
document.getElementById('exportBtn').addEventListener('click', async () => {
  try {
    const data = await editor.save();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), {
      href: url,
      download: `editorjs-${new Date().toISOString().replace(/[:.]/g,'-')}.json`
    });
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  } catch (e) { alert('Nie udało się zapisać: ' + e.message); console.error(e); }
});

// --- SANITYZACJA DANYCH PRZED WCZYTANIEM ---
function sanitizeData(data) {
  if (!data || !Array.isArray(data.blocks)) {
    return { time: Date.now(), blocks: [] };
  }

  const TRAINING_TEMPLATE = {
    withHeadings: true,
    content: [
      ['Ćwiczenie', 'Powtórzenia', 'Kg'],
      ['1/2 przysiad', '10/8/6', '100/110/120 kg']
    ]
  };

  const blocks = data.blocks.map((b) => {
    if (b.type === 'workoutTable') {
      return { type: 'table', data: { ...TRAINING_TEMPLATE } };
    }
    if (b.type === 'table' && b.data && Array.isArray(b.data.content)) {
      const rows = b.data.content;
      const minCols = 1;
      const maxCols = Math.max(minCols, ...rows.map(r => Array.isArray(r) ? r.length : 0));
      const fixed = rows.map(r => {
        const row = Array.isArray(r) ? r.slice(0, maxCols) : [];
        while (row.length < maxCols) row.push('');
        return row;
      });
      return { ...b, data: { ...b.data, content: fixed } };
    }
    return b;
  });

  return { ...data, blocks };
}

// --- IMPORT ---
document.getElementById('importFile').addEventListener('change', async (ev) => {
  const file = ev.target.files?.[0];
  if (!file) return;
  try {
    const txt = await file.text();
    const json = JSON.parse(txt);
    const clean = sanitizeData(json);
    await editor.isReady;
    await editor.render(clean);
  } catch (e) {
    alert('Niepoprawny JSON Editor.js lub błąd wczytywania.');
    console.error(e);
  } finally {
    ev.target.value = '';
  }
});
