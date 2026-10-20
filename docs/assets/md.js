/*
 * OpenCue website – md.js
 * A small, safe Markdown renderer for the texts the site loads from GitHub (CHANGELOG.md, help guides).
 * Supports: headings, paragraphs, bold/italic, inline code, links, fenced code, block quotes,
 * bullet and numbered lists (nested by indentation), pipe tables, horizontal rules.
 * Safety: all text is HTML-escaped FIRST; only the tags generated below ever reach innerHTML,
 * and links are limited to http(s), mailto, anchors and relative paths.
 *
 *   OCMarkdown.render(text, { base: "https://github.com/…/blob/main/" })
 *     -> { html: "<h2 id=…>…", headings: [{ level, text, id }] }
 */
(function (g) {
  "use strict";

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function slug(text) {
    return String(text).toLowerCase().replace(/<[^>]*>/g, "").replace(/[`*_]/g, "")
      .replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-+|-+$/g, "") || "section";
  }

  function safeHref(raw, base) {
    var u = raw.replace(/&amp;/g, "&");
    if (/^(https?:|mailto:)/i.test(u)) { return u; }
    if (u.charAt(0) === "#") { return u; }
    if (/^[a-z][a-z0-9+.-]*:/i.test(u)) { return null; }          // javascript:, data:, …
    if (base) { try { return new URL(u, base).href; } catch (e) { return null; } }
    return u;
  }

  function inline(raw, base) {
    var codes = [];
    var s = String(raw).replace(/`([^`]+)`/g, function (_, c) { codes.push(c); return "\u0000" + (codes.length - 1) + "\u0000"; });
    s = esc(s);
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (_, text, href) {
      var safe = safeHref(href, base);
      return safe ? '<a href="' + esc(safe) + '" rel="noopener">' + text + "</a>" : text;
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*\w])\*([^*\s][^*]*)\*(?!\w)/g, "$1<em>$2</em>");
    s = s.replace(/\u0000(\d+)\u0000/g, function (_, i) { return "<code>" + esc(codes[Number(i)]) + "</code>"; });
    return s;
  }

  function splitRow(line) {
    var cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/);
    return cells.map(function (c) { return c.replace(/\\\|/g, "|").trim(); });
  }

  // ---- syntax colours for effect scripts (same classes as the Effect Studio: static/css/style.css --fxs-hl-*)
  var FX_KEYWORDS = /^(if|else|for|while|do|break|continue|return|void|float|double|int|long|short|byte|bool|boolean|const|true|false|Slider|NumberInput|ColorPicker|Internal|setup|loop)$/;
  var FX_CONSTS = /^(PI|TWO_PI|HALF_PI|E)$/;
  var FX_OUTPUTS = /^(dimmer|r|g|b|pan|tilt|zoom|focus|gobo|gobo_spin|gobo2|gobo2_spin|color|position)$/;
  var FX_SYSTEM = /^(t|elapsed|dt|tick|loop_count|rate|index|count|phase|slots|slots2)$/;
  var TOKEN = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/)|(#[A-Za-z_]+)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|([\s\S])/g;

  function highlight(code) {
    var out = "", m;
    TOKEN.lastIndex = 0;
    while ((m = TOKEN.exec(code)) !== null) {
      if (m[1]) { out += '<span class="hl-c">' + esc(m[1]) + "</span>"; }
      else if (m[2]) { out += '<span class="hl-d">' + esc(m[2]) + "</span>"; }
      else if (m[3]) { out += '<span class="hl-p">' + esc(m[3]) + "</span>"; }
      else if (m[4]) {
        var word = m[4], next = code.charAt(TOKEN.lastIndex), cls = "";
        if (FX_CONSTS.test(word) || FX_KEYWORDS.test(word)) { cls = "hl-k"; }
        else if (FX_OUTPUTS.test(word)) { cls = "hl-o"; }
        else if (FX_SYSTEM.test(word)) { cls = "hl-s"; }
        else if (next === "(") { cls = "hl-f"; }
        out += cls ? '<span class="' + cls + '">' + esc(word) + "</span>" : esc(word);
      }
      else { out += esc(m[5]); }
    }
    return out;
  }

  function codeBlock(code, lang) {
    var label = lang || "code";
    return '<figure class="code-block" data-label="' + esc(label) + '"><pre><code>' + highlight(code) + "</code></pre></figure>";
  }

  var RE_LIST = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;

  function render(text, opts) {
    var base = opts && opts.base;
    var lines = String(text).replace(/\r\n?/g, "\n").split("\n");
    var out = [];
    var headings = [];
    var used = {};
    var i = 0;

    function uniqueId(t) {
      var id = slug(t), n = 1, candidate = id;
      while (used[candidate]) { n += 1; candidate = id + "-" + n; }
      used[candidate] = true;
      return candidate;
    }

    // list lines starting at i -> html; items nest by indentation
    function list(start) {
      var items = [];
      var j = start;
      while (j < lines.length) {
        var m = RE_LIST.exec(lines[j]);
        if (m) {
          items.push({ indent: m[1].replace(/\t/g, "    ").length, ordered: /\d/.test(m[2]), text: m[3] });
          j += 1;
        } else if (/^\s+\S/.test(lines[j]) && items.length && !/^\s*```/.test(lines[j])) {
          items[items.length - 1].text += " " + lines[j].trim();       // wrapped continuation line
          j += 1;
        } else { break; }
      }
      var pos = 0;
      function build(minIndent) {
        var tag = items[pos].ordered ? "ol" : "ul";
        var htmlOut = "<" + tag + ">";
        var indent = items[pos].indent;
        while (pos < items.length && items[pos].indent >= indent) {
          if (items[pos].indent > indent) { break; }
          var item = items[pos];
          pos += 1;
          var inner = inline(item.text, base);
          if (pos < items.length && items[pos].indent > indent) { inner += build(indent + 1); }
          htmlOut += "<li>" + inner + "</li>";
        }
        return htmlOut + "</" + tag + ">";
      }
      var htmlList = "";
      while (pos < items.length) { htmlList += build(0); }
      return { html: htmlList, next: j };
    }

    while (i < lines.length) {
      var line = lines[i];

      if (/^\s*$/.test(line)) { i += 1; continue; }

      var fence = /^\s*```\s*([\w-]*)\s*$/.exec(line);
      if (fence) {
        var code = [];
        i += 1;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) { code.push(lines[i]); i += 1; }
        i += 1;
        out.push(codeBlock(code.join("\n"), fence[1]));
        continue;
      }

      var h = /^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(line);
      if (h) {
        var level = h[1].length;
        var id = uniqueId(h[2]);
        headings.push({ level: level, text: h[2].replace(/[`*]/g, ""), id: id });
        out.push("<h" + level + ' id="' + id + '">' + inline(h[2], base) + "</h" + level + ">");
        i += 1;
        continue;
      }

      if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { out.push("<hr>"); i += 1; continue; }

      if (/^\s*>/.test(line)) {
        var quote = [];
        while (i < lines.length && /^\s*>/.test(lines[i])) { quote.push(lines[i].replace(/^\s*>\s?/, "")); i += 1; }
        out.push("<blockquote>" + render(quote.join("\n"), opts).html + "</blockquote>");
        continue;
      }

      if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i + 1])) {
        var head = splitRow(line);
        i += 2;
        var rows = [];
        while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(splitRow(lines[i])); i += 1; }
        var table = '<div class="table-wrap"><table><thead><tr>' +
          head.map(function (c) { return "<th>" + inline(c, base) + "</th>"; }).join("") + "</tr></thead><tbody>" +
          rows.map(function (r) { return "<tr>" + r.map(function (c) { return "<td>" + inline(c, base) + "</td>"; }).join("") + "</tr>"; }).join("") +
          "</tbody></table></div>";
        out.push(table);
        continue;
      }

      if (RE_LIST.test(line)) {
        var result = list(i);
        out.push(result.html);
        i = result.next;
        continue;
      }

      var para = [line.trim()];
      i += 1;
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !/^\s*(#{1,6}\s|```|>|\|)/.test(lines[i]) && !RE_LIST.test(lines[i])) {
        para.push(lines[i].trim());
        i += 1;
      }
      out.push("<p>" + inline(para.join(" "), base) + "</p>");
    }

    return { html: out.join("\n"), headings: headings };
  }

  g.OCMarkdown = { render: render, escape: esc, highlight: highlight };
})(window);
