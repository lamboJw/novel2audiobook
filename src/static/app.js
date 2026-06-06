const API = "/api";
let state = { novels: [], currentNovelId: null, chapters: [], sentences: [], currentIndex: -1, audio: null, playing: false };

async function json(path) { const r = await fetch(API + path); return r.json(); }

async function loadNovels() {
  const novels = await json("/novels");
  state.novels = novels;
  document.getElementById("novel-list").innerHTML = novels.map(n =>
    `<li onclick="selectNovel(${n.id})" class="${state.currentNovelId === n.id ? 'active' : ''}">
      ${esc(n.title)} <span class="status-badge ${n.status === 'done' ? 'done' : ''}">${n.status}</span>
    </li>`
  ).join("");
}

async function selectNovel(id) {
  state.currentNovelId = id;
  const data = await json(`/novels/${id}`);
  state.chapters = data.chapters || [];
  document.getElementById("chapter-list").innerHTML = state.chapters.map(ch =>
    `<li onclick="loadChapter(${data.id}, ${ch.id})">
      第${ch.index}章 ${esc(ch.title)}
      <span class="status-badge ${ch.status === 'done' ? 'done' : ''}">${ch.status}</span>
    </li>`
  ).join("");
  loadNovels();
}

async function loadChapter(novelId, chapterId) {
  const sentences = await json(`/novels/${novelId}/chapters/${chapterId}/sentences`);
  state.sentences = sentences;
  state.currentIndex = -1;
  document.getElementById("reader").innerHTML = sentences.map((s, i) =>
    `<span class="sentence" data-index="${i}" onclick="playSentence(${i})">${esc(s.text)}</span> `
  ).join("");
}

function esc(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function playSentence(index) {
  const s = state.sentences[index];
  if (!s || !s.audio_url) return;
  stopPlayback();
  state.currentIndex = index;
  document.querySelectorAll(".sentence").forEach(el => el.classList.remove("playing"));
  document.querySelector(`.sentence[data-index="${index}"]`)?.classList.add("playing");
  document.getElementById("sentence-info").textContent = `${index + 1}/${state.sentences.length}`;
  state.audio = new Audio(s.audio_url);
  state.audio.onended = () => {
    if (state.currentIndex < state.sentences.length - 1) {
      playSentence(state.currentIndex + 1);
    } else {
      state.playing = false;
      document.getElementById("play-btn").textContent = "▶";
    }
  };
  state.audio.play();
  state.playing = true;
  document.getElementById("play-btn").textContent = "⏸";
}

function stopPlayback() {
  if (state.audio) { state.audio.pause(); state.audio = null; }
  state.playing = false;
  document.getElementById("play-btn").textContent = "▶";
}

document.getElementById("play-btn").onclick = () => {
  if (!state.sentences.length) return;
  if (state.playing) { stopPlayback(); return; }
  playSentence(state.currentIndex >= 0 ? state.currentIndex : 0);
};

function showUpload() {
  document.getElementById("upload-modal").classList.add("show");
}

document.getElementById("upload-form").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData();
  fd.append("file", document.getElementById("file-input").files[0]);
  fd.append("title", document.getElementById("title-input").value);
  fd.append("author", document.getElementById("author-input").value);
  await fetch(API + "/novels", { method: "POST", body: fd });
  document.getElementById("upload-modal").classList.remove("show");
  document.getElementById("file-input").value = "";
  document.getElementById("title-input").value = "";
  document.getElementById("author-input").value = "";
  loadNovels();
};

document.getElementById("upload-modal").onclick = (e) => {
  if (e.target === e.currentTarget) e.currentTarget.classList.remove("show");
};

loadNovels();
