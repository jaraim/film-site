/* ============================================================
 * 通用影视播放器播放器组件 (Universal Film Player)
 * 无第三方依赖，基于原生 HTML5 <video>
 *
 * 功能：
 *   1. 跳片头：自动跳过片头 N 秒（可设置）
 *   2. 跳片尾：接近结尾 N 秒时自动跳转到结局并暂停/连播
 *   3. 播放倍速：0.5x ~ 2.0x 循环切换 + 自定义
 *   4. 连播：本片源自动播下一集；最后一集则尝试下一个资源或停止
 *   5. 资源切换：多播放源(线路)切换，保留当前集数
 *   6. 记忆：localStorage 记住播放进度、倍速、片头/片尾设置、所选线路与集数
 *   7. 方向键/空格快捷键
 *
 * 使用：
 *   const player = new FilmPlayer(videoEl, {
 *       sources: [...],      // 所有线路 [{flag,name,episodes:[{n,name,url}]}]
 *       currentFlag: '...',  // 当前线路
 *       ep: 1,               // 当前集数
 *       video: {id, title, skipIntro, skipOutro},
 *       autoNext: true,      // 是否自动连播
 *       onSwitch: fn         // 切换集/线路时回调(flag, ep)
 *   });
 * ============================================================ */

(function (global) {
  "use strict";

  const STORE_KEY = "film_player_state";
  const RATES = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

  class FilmPlayer {
    constructor(videoEl, opts) {
      if (!videoEl) throw new Error("video element required");
      this.video = videoEl;
      this.opts = Object.assign(
        {
          sources: [],
          currentFlag: "",
          ep: 1,
          video: { id: 0, title: "", skipIntro: 0, skipOutro: 0 },
          autoNext: true,
          onSwitch: function () {},
        },
        opts || {}
      );

      // 播放设置（片头/片尾，持久化）
      this.settings = this._loadSettings();
      if (!this.settings.skipIntro) this.settings.skipIntro = this.opts.video.skipIntro || 0;
      if (!this.settings.skipOutro) this.settings.skipOutro = this.opts.video.skipOutro || 0;

      this.currentFlag = this.opts.currentFlag || this._firstFlag();
      this.currentEp = this.opts.ep || 1;
      this._bindEvents();
      this._buildUI();
      this.loadEpisode(this.currentEp, false);
    }

    // ---------- 数据访问 ----------
    _firstFlag() {
      return this.opts.sources.length ? this.opts.sources[0].flag : "";
    }
    get source() {
      return this.opts.sources.find((s) => s.flag === this.currentFlag) || null;
    }
    get episode() {
      if (!this.source) return null;
      return this.source.episodes.find((e) => e.n === this.currentEp) || null;
    }
    get lastEp() {
      return this.source ? this.source.episodes.length : 0;
    }

    // ---------- 持久化 ----------
    _loadSettings() {
      try {
        const d = JSON.parse(global.localStorage.getItem(STORE_KEY) || "{}");
        return {
          skipIntro: d.skipIntro || 0,
          skipOutro: d.skipOutro || 0,
          rate: d.rate || 1,
          videoState: d.videoState || {},
        };
      } catch (e) {
        return { skipIntro: 0, skipOutro: 0, rate: 1, videoState: {} };
      }
    }
    _saveSettings() {
      try {
        const d = JSON.parse(global.localStorage.getItem(STORE_KEY) || "{}");
        d.skipIntro = this.settings.skipIntro;
        d.skipOutro = this.settings.skipOutro;
        d.rate = this.settings.rate;
        d.videoState = this.settings.videoState;
        global.localStorage.setItem(STORE_KEY, JSON.stringify(d));
      } catch (e) {}
    }
    _memKey() {
      return `fp:${this.opts.video.id}:${this.currentFlag}`;
    }

    // ---------- 事件 ----------
    _bindEvents() {
      this.video.addEventListener("timeupdate", () => this._onTimeUpdate());
      this.video.addEventListener("loadedmetadata", () => this._onMeta());
      this.video.addEventListener("play", () => this._onPlay());
      this.video.addEventListener("ended", () => this._onEnded());
      this.video.addEventListener("error", () => this._onError());
    }

    _onMeta() {
      // 恢复本集进度
      const mem = this.settings.videoState[this._memKey()] || {};
      if (mem[this.currentEp] && mem[this.currentEp] > 3) {
        const t = mem[this.currentEp];
        const d = this.video.duration;
        if (t < d - 10) this.video.currentTime = t;
      }
    }
    _onPlay() {
      this.video.playbackRate = this.settings.rate;
    }
    _onTimeUpdate() {
      // 跳片头：只在开头触发一次
      const si = this.settings.skipIntro;
      if (si > 0 && this.video.currentTime > 0.2 && this.video.currentTime < si && this.video.currentTime < this.video.duration * 0.6) {
        if (!this._introJumped) {
          this._introJumped = true;
          this.video.currentTime = si;
          if (this.opts.onIntroSkip) this.opts.onIntroSkip(si);
        }
      } else if (this.video.currentTime >= si + 1) {
        this._introJumped = true;
      }

      // 跳片尾：接近末尾，跳到结局
      const so = this.settings.skipOutro;
      if (so > 0 && this.video.duration > 0) {
        const remain = this.video.duration - this.video.currentTime;
        if (remain > 0.3 && remain <= so) {
          this._skipOutro();
        }
      }

      // 记忆进度（节流）
      if (!this._savedAt || this.video.currentTime - this._savedAt > 3) {
        this._savedAt = this.video.currentTime;
        if (!this.settings.videoState[this._memKey()])
          this.settings.videoState[this._memKey()] = {};
        this.settings.videoState[this._memKey()][this.currentEp] = this.video.currentTime;
        this._saveSettings();
      }
    }
    _skipOutro() {
      this.video.currentTime = this.video.duration - 0.2;
      if (this._outroSkipped) return;
      this._outroSkipped = true;
      this._showToast(`已跳过片尾`);
    }
    _onEnded() {
      this.video.currentTime = 0;
      if (this.opts.autoNext) {
        if (this.currentEp < this.lastEp) {
          this.loadEpisode(this.currentEp + 1);
          this._showToast("连播下一集");
        } else {
          this._nextSource();
        }
      }
    }
    _onError() {
      // 播放失败：尝试切换同片下一个资源
      this._showToast("当前线路播放失败，尝试切换线路");
      this._nextSource();
    }

    // ---------- 集/线路切换 ----------
    loadEpisode(ep, autoplay) {
      if (!this.source) return;
      const max = this.lastEp;
      ep = Math.max(1, Math.min(ep || 1, max || 1));
      this.currentEp = ep;
      this._introJumped = false;
      this._outroSkipped = false;
      const epObj = this.episode;
      if (epObj) {
        this.video.src = epObj.url;
        this.video.load();
        if (autoplay !== false) this.video.play().catch(() => {});
      }
      if (this.opts.onSwitch)
        this.opts.onSwitch(this.currentFlag, this.currentEp);
    }

    switchSource(flag) {
      if (flag === this.currentFlag) return;
      this.currentFlag = flag;
      // 尝试保留集数，超出则取第1集
      const s = this.source;
      let ep = this.currentEp;
      if (s && ep > s.episodes.length) ep = 1;
      this.currentEp = ep;
      this.loadEpisode(ep);
    }

    _nextSource() {
      const idx = this.opts.sources.findIndex((s) => s.flag === this.currentFlag);
      const next = this.opts.sources[(idx + 1) % this.opts.sources.length];
      if (next && next.flag !== this.currentFlag) {
        this.switchSource(next.flag);
        this._showToast("切换线路：" + next.name);
      }
    }

    // ---------- 控制接口 ----------
    setRate(rate) {
      rate = Math.max(0.25, Math.min(3, rate || 1));
      this.settings.rate = rate;
      this.video.playbackRate = rate;
      this._saveSettings();
      this._updateRateUI();
    }
    cycleRate() {
      let r = this.settings.rate;
      let ni = RATES.indexOf(r) + 1;
      if (ni >= RATES.length) ni = 0;
      this.setRate(RATES[ni]);
    }
    setSkipIntro(sec) {
      this.settings.skipIntro = Math.max(0, parseFloat(sec) || 0);
      this._saveSettings();
      this._updateSkipUI();
      this._showToast("片头跳过已设为 " + this.settings.skipIntro + " 秒");
    }
    setSkipOutro(sec) {
      this.settings.skipOutro = Math.max(0, parseFloat(sec) || 0);
      this._saveSettings();
      this._updateSkipUI();
      this._showToast("片尾跳过已设为 " + this.settings.skipOutro + " 秒");
    }
    toggleAutoNext() {
      this.opts.autoNext = !this.opts.autoNext;
      const el = this.ui.autoNextBtn;
      if (el) {
        el.classList.toggle("active", this.opts.autoNext);
        el.textContent = this.opts.autoNext ? "连播:开" : "连播:关";
      }
    }

    // ---------- UI 构建 ----------
    _buildUI() {
      const wrap = document.createElement("div");
      wrap.className = "fp-wrap";
      this.video.parentNode.insertBefore(wrap, this.video);
      wrap.appendChild(this.video);

      // 顶层容器包裹 video，控制条叠加
      const controls = document.createElement("div");
      controls.className = "fp-controls";
      wrap.appendChild(controls);

      const b = (label, cls, cb) => {
        const btn = document.createElement("button");
        btn.className = "fp-btn " + (cls || "");
        btn.textContent = label;
        btn.addEventListener("click", cb);
        return btn;
      };

      const bar = document.createElement("div");
      bar.className = "fp-bar";
      controls.appendChild(bar);

      // 播放/暂停
      const playBtn = b("播放", "", () => {
        if (this.video.paused) this.video.play();
        else this.video.pause();
      });
      bar.appendChild(playBtn);
      this.ui = { playBtn };

      // 倍速
      const rateBtn = b("1.0x", "rate", () => this.cycleRate());
      rateBtn.title = "倍速（点击切换）";
      bar.appendChild(rateBtn);
      this.ui.rateBtn = rateBtn;

      // 片头/片尾设置按钮 → 弹出设置面板
      const skipBtn = b("跳过", "skip", () => this._togglePanel());
      skipBtn.title = "片头/片尾时间设置";
      bar.appendChild(skipBtn);

      // 连播开关
      const autoBtn = b(this.opts.autoNext ? "连播:开" : "连播:关", "auto active", () => this.toggleAutoNext());
      autoBtn.title = "自动连播下一集";
      bar.appendChild(autoBtn);

      // 线路切换下拉
      if (this.opts.sources.length > 1) {
        const sel = document.createElement("select");
        sel.className = "fp-source";
        this.opts.sources.forEach((s) => {
          const o = document.createElement("option");
          o.value = s.flag;
          o.textContent = s.name;
          sel.appendChild(o);
        });
        sel.value = this.currentFlag;
        sel.addEventListener("change", () => this.switchSource(sel.value));
        bar.appendChild(sel);
        this.ui.sourceSel = sel;
      }

      // 全屏
      const fullBtn = b("全屏", "", () => this._toggleFullscreen(wrap));
      bar.appendChild(fullBtn);

      // 设置面板（片头/片尾）
      const panel = document.createElement("div");
      panel.className = "fp-panel";
      panel.style.display = "none";
      controls.appendChild(panel);

      const mkInput = (label, val, cb) => {
        const row = document.createElement("div");
        row.className = "fp-prow";
        const lab = document.createElement("span");
        lab.textContent = label;
        const inp = document.createElement("input");
        inp.type = "number";
        inp.min = "0";
        inp.step = "0.5";
        inp.value = val;
        inp.addEventListener("change", () => cb(inp.value));
        row.appendChild(lab);
        row.appendChild(inp);
        return row;
      };
      panel.appendChild(mkInput("片头跳过(秒)", this.settings.skipIntro, (v) => this.setSkipIntro(v)));
      panel.appendChild(mkInput("片尾跳过(秒)", this.settings.skipOutro, (v) => this.setSkipOutro(v)));

      // 提示 toast
      const toast = document.createElement("div");
      toast.className = "fp-toast";
      wrap.appendChild(toast);
      this.ui.toast = toast;

      this.ui.wrap = wrap;
      this.ui.panel = panel;
      this._updateRateUI();
      this._updateSkipUI();

      // 快捷键
      this._bindKeys(wrap);
    }

    _togglePanel() {
      this.ui.panel.style.display = this.ui.panel.style.display === "none" ? "block" : "none";
    }
    _toggleFullscreen(wrap) {
      if (document.fullscreenElement) document.exitFullscreen();
      else wrap.requestFullscreen && wrap.requestFullscreen();
    }
    _bindKeys(wrap) {
      document.addEventListener("keydown", (e) => {
        if (document.activeElement && /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) return;
        if (e.code === "Space") { e.preventDefault(); if (this.video.paused) this.video.play(); else this.video.pause(); }
        else if (e.key === "ArrowRight") this.video.currentTime += 10;
        else if (e.key === "ArrowLeft") this.video.currentTime -= 10;
        else if (e.key === "ArrowUp") this.video.volume = Math.min(1, this.video.volume + 0.1);
        else if (e.key === "ArrowDown") this.video.volume = Math.max(0, this.video.volume - 0.1);
      });
    }

    _updateRateUI() {
      if (this.ui.rateBtn) this.ui.rateBtn.textContent = this.settings.rate.toFixed(2).replace(/0+$/, "").replace(/\.$/, "") + "x";
    }
    _updateSkipUI() {
      // 面板内已有输入框，直接刷新（通过重新赋值）
    }

    _showToast(msg) {
      const t = this.ui.toast;
      t.textContent = msg;
      t.classList.add("show");
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
    }

    // 外部可读状态
    getState() {
      return { flag: this.currentFlag, ep: this.currentEp, rate: this.settings.rate };
    }
  }

  global.FilmPlayer = FilmPlayer;
})(window);
