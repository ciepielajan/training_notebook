/** Narzędzie “Tabela treningowa” – widoczne w plusie */
class WorkoutTableTool {
  static get toolbox() {
    return {
      title: 'Tabela treningowa',
      icon: '<svg width="17" height="17" viewBox="0 0 24 24"><path d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm0 3v3h16V8H4zm0 5v4h16v-4H4z" fill="currentColor"/></svg>',
    };
  }

  constructor({ api }) {
    this.api = api;
    this.template = {
      withHeadings: true,
      workoutTable: true,
      content: [
        ['Ćwiczenie', 'Powtórzenia', 'Kg'],
        ['1/2 przysiad', '10/8/6', '100/110/120 kg'],
      ],
    };
  }

  render() {
    const phantom = document.createElement('div');
    phantom.style.display = 'none';
    requestAnimationFrame(() => {
      const idx = this.api.blocks.getCurrentBlockIndex();
      this.api.blocks.insert('table', this.template, {}, idx, true);
      this.api.caret.setToBlock(idx, 'end');
      scheduleWorkoutMark(idx);
    });
    return phantom;
  }

  save() {
    return {};
  }
}

function markWorkoutTable(idx, attempt = 0) {
  if (attempt > 20) return;
  const blocks = document.querySelectorAll('.codex-editor .ce-block');
  const block = blocks[idx];
  if (!block) {
    requestAnimationFrame(() => markWorkoutTable(idx, attempt + 1));
    return;
  }
  block.dataset.workoutTable = 'true';
  const wrap = block.querySelector('.tc-wrap');
  if (!wrap) {
    const delay = attempt < 5 ? 16 : 120;
    setTimeout(() => markWorkoutTable(idx, attempt + 1), delay);
    return;
  }
  wrap.classList.add('workout-table');
  ensureWorkoutColumnMenu(block, idx);
}

function scheduleWorkoutMark(idx) {
  requestAnimationFrame(() => markWorkoutTable(idx));
}

const WORKOUT_COLUMN_PRESETS = [
  { id: 'odcinek', label: 'Odcinek', columns: ['+', '', 'm', '', 'sec.'] },
  { id: 'cwiczenie', label: 'Ćwiczenie', columns: ['', 'm', ''] },
  { id: 'przerwa', label: 'Przerwa', columns: ['-p', '', 'min'] },
  { id: 'tetno', label: 'Tętno', columns: ['hr', '', 'hr/min', '', 'min'] },
];

let workoutMenuCloseListenerAttached = false;

function ensureWorkoutColumnMenu(block, idx, attempt = 0) {
  if (attempt > 20) return;
  const wrap = block.querySelector('.tc-wrap');
  const addBtn = block.querySelector('.tc-add-column');
  if (!wrap || !addBtn) {
    const delay = attempt < 5 ? 20 : 140;
    setTimeout(() => ensureWorkoutColumnMenu(block, idx, attempt + 1), delay);
    return;
  }

  if (addBtn.dataset.workoutMenuReady === 'true') return;
  addBtn.dataset.workoutMenuReady = 'true';

  if (!workoutMenuCloseListenerAttached) {
    document.addEventListener('click', (event) => {
      document
        .querySelectorAll('.workout-column-menu.is-open')
        .forEach((menu) => {
          const trigger = menu.parentElement;
          if (trigger?.contains(event.target)) return;
          if (menu.contains(event.target)) return;
          menu.classList.remove('is-open');
        });
    });
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      closeWorkoutMenus();
    });
    workoutMenuCloseListenerAttached = true;
  }

  addBtn.classList.add('workout-table__add');
  addBtn.style.position = 'relative';

  const menu = document.createElement('div');
  menu.className = 'workout-column-menu';
  menu.setAttribute('role', 'menu');

  WORKOUT_COLUMN_PRESETS.forEach((preset) => {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = 'workout-column-menu__item';
    option.textContent = preset.label;
    option.dataset.presetId = preset.id;
    option.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      closeWorkoutMenus();
      await applyWorkoutPresetToBlock(block, preset.columns);
    });
    menu.appendChild(option);
  });

  addBtn.appendChild(menu);

  const intercept = (event) => {
    if (block.dataset.workoutAdding === 'true') {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    toggleWorkoutMenu(menu);
  };

  ['pointerdown', 'mousedown', 'click'].forEach((evtName) => {
    addBtn.addEventListener(evtName, intercept, true);
  });
}

function toggleWorkoutMenu(menu) {
  const isOpen = menu.classList.contains('is-open');
  closeWorkoutMenus(menu);
  if (!isOpen) {
    menu.classList.add('is-open');
  }
}

function closeWorkoutMenus(except) {
  document.querySelectorAll('.workout-column-menu.is-open').forEach((menu) => {
    if (menu === except) return;
    menu.classList.remove('is-open');
  });
}

async function applyWorkoutPresetToBlock(blockEl, columns) {
  if (!columns?.length) return;

  const blockIndex = getBlockIndexFromElement(blockEl);
  if (blockIndex === -1) return;

  blockEl.dataset.workoutAdding = 'true';
  closeWorkoutMenus();

  const blockApi = editor.blocks.getBlockByIndex(blockIndex);
  if (!blockApi || typeof blockApi.save !== 'function') {
    delete blockEl.dataset.workoutAdding;
    return;
  }

  let saved;
  try {
    saved = await blockApi.save();
  } catch (error) {
    console.error('Nie udało się odczytać danych tabeli:', error);
    delete blockEl.dataset.workoutAdding;
    return;
  }

  const tableData = saved?.data || {};
  const content = Array.isArray(tableData.content)
    ? tableData.content.map((row) => (Array.isArray(row) ? [...row] : []))
    : [];

  const normalizedContent = content.length ? content : [[]];
  const rowsNormalized = normalizeRows(normalizedContent);
  const appendedContent = rowsNormalized.map((row, rowIndex) => {
    const nextRow = row.slice();
    columns.forEach((value) => {
      nextRow.push(rowIndex === 0 ? value : '');
    });
    return nextRow;
  });

  const updatedData = {
    ...tableData,
    withHeadings: tableData.withHeadings !== false,
    workoutTable: true,
    content: normalizeRows(appendedContent),
  };

  editor.blocks.insert('table', updatedData, {}, blockIndex, true);

  requestAnimationFrame(() => {
    scheduleWorkoutMark(blockIndex);
    editor.caret.setToBlock(blockIndex, 'end');
    const refreshedBlock = document.querySelectorAll('.codex-editor .ce-block')[
      blockIndex
    ];
    if (refreshedBlock) {
      delete refreshedBlock.dataset.workoutAdding;
    }
  });
}

function normalizeRows(rows) {
  if (!rows.length) return [[]];
  const maxCols = Math.max(...rows.map((row) => row.length));
  return rows.map((row) => {
    const normalized = row.slice(0, maxCols);
    while (normalized.length < maxCols) {
      normalized.push('');
    }
    return normalized;
  });
}

function getBlockIndexFromElement(blockEl) {
  const blocks = Array.from(
    document.querySelectorAll('.codex-editor .ce-block')
  );
  return blocks.indexOf(blockEl);
}

// Inicjalizacja
const editor = new EditorJS({
  holder: 'editor',
  autofocus: true,
  tools: {
    paragraph: {
      class: Paragraph,
      inlineToolbar: true,
      config: { placeholder: 'Napisz coś…' },
    },
    table: { class: Table, inlineToolbar: true },
    workoutTable: { class: WorkoutTableTool },
  },
});

editor.isReady
  .then(() => editor.save())
  .then((data) => markWorkoutTablesFromData(data))
  .catch(() => {});

// Szybkie przyciski
document.getElementById('addText').onclick = () => {
  const i = editor.blocks.getBlocksCount();
  editor.blocks.insert('paragraph', { text: '' }, {}, i, true);
};
document.getElementById('addTable').onclick = () => {
  const i = editor.blocks.getBlocksCount();
  editor.blocks.insert(
    'table',
    {
      withHeadings: true,
      content: [
        ['Heading', 'Heading', 'Heading'],
        ['', '', ''],
      ],
    },
    {},
    i,
    true
  );
};
document.getElementById('addWorkout').onclick = () => {
  const i = editor.blocks.getBlocksCount();
  editor.blocks.insert(
    'table',
    {
      withHeadings: true,
      workoutTable: true,
      content: [
        ['Ćwiczenie', 'Powtórzenia', 'Kg'],
        ['1/2 przysiad', '10/8/6', '100/110/120 kg'],
      ],
    },
    {},
    i,
    true
  );
  scheduleWorkoutMark(i);
};

// Eksport
document.getElementById('exportBtn').addEventListener('click', async () => {
  try {
    const data = await editor.save();
    applyWorkoutFlagToExport(data);
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), {
      href: url,
      download: `editorjs-${new Date()
        .toISOString()
        .replace(/[:.]/g, '-')}.json`,
    });
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('Nie udało się zapisać: ' + e.message);
    console.error(e);
  }
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
      ['1/2 przysiad', '10/8/6', '100/110/120 kg'],
    ],
  };

  const blocks = data.blocks.map((b) => {
    if (b.type === 'workoutTable') {
      return { type: 'table', data: { ...TRAINING_TEMPLATE } };
    }
    if (b.type === 'table' && b.data && Array.isArray(b.data.content)) {
      const rows = b.data.content;
      const minCols = 1;
      const maxCols = Math.max(
        minCols,
        ...rows.map((r) => (Array.isArray(r) ? r.length : 0))
      );
      const fixed = rows.map((r) => {
        const row = Array.isArray(r) ? r.slice(0, maxCols) : [];
        while (row.length < maxCols) row.push('');
        return row;
      });
      const normalized = { ...b.data, content: fixed };
      if ('workoutTable' in b.data) {
        normalized.workoutTable = Boolean(b.data.workoutTable);
      }
      return { ...b, data: normalized };
    }
    return b;
  });

  return { ...data, blocks };
}

function markWorkoutTablesFromData(data) {
  if (!data || !Array.isArray(data.blocks)) return;
  data.blocks.forEach((block, idx) => {
    if (block.type === 'table' && block.data?.workoutTable) {
      scheduleWorkoutMark(idx);
    }
  });
}

function applyWorkoutFlagToExport(data) {
  if (!data || !Array.isArray(data.blocks)) return;
  const domBlocks = document.querySelectorAll('.codex-editor .ce-block');
  data.blocks = data.blocks.map((block, idx) => {
    if (block.type !== 'table') return block;
    const domBlock = domBlocks[idx];
    const isWorkout = domBlock?.dataset?.workoutTable === 'true';
    if (isWorkout) {
      return {
        ...block,
        data: { ...block.data, workoutTable: true },
      };
    }
    if (block.data && 'workoutTable' in block.data) {
      const { workoutTable, ...rest } = block.data;
      return { ...block, data: rest };
    }
    return block;
  });
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
    requestAnimationFrame(() => markWorkoutTablesFromData(clean));
  } catch (e) {
    alert('Niepoprawny JSON Editor.js lub błąd wczytywania.');
    console.error(e);
  } finally {
    ev.target.value = '';
  }
});
