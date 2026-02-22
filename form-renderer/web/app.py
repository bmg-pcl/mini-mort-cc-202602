"""Streamlit web app — renders survey.js forms as native controls + WebGPU chat."""

import json
import sys
from pathlib import Path

import requests
import streamlit as st

# Allow imports from parent package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forms import DEFAULT_FORM, get_all_elements, load_form, validate_responses

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Form Renderer", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar — mode selector
# ---------------------------------------------------------------------------
mode = st.sidebar.radio("Mode", ["Form", "Chat (WebGPU LLM)"])
api_url = st.sidebar.text_input("API URL", value="http://localhost:8000")
form_file = st.sidebar.file_uploader("Upload survey.js JSON", type=["json"])

if form_file is not None:
    form_def = json.load(form_file)
else:
    form_def = load_form(DEFAULT_FORM)

# ===================================================================
# MODE 1 — Survey.js form rendered as Streamlit widgets
# ===================================================================
if mode == "Form":
    st.title(form_def.get("title", "Survey"))
    if form_def.get("description"):
        st.markdown(form_def["description"])

    responses: dict = {}
    pages = form_def.get("pages", [])
    total_pages = len(pages)

    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    # Progress bar
    if form_def.get("showProgressBar") and total_pages > 0:
        st.progress((st.session_state.current_page + 1) / total_pages)

    page = pages[st.session_state.current_page]
    st.subheader(page.get("title", f"Page {st.session_state.current_page + 1}"))

    for el in page.get("elements", []):
        etype = el.get("type", "text")
        name = el["name"]
        title = el.get("title", name)
        required = el.get("isRequired", False)
        label = f"{title} *" if required else title

        if etype == "text":
            input_type = el.get("inputType", "text")
            val = st.text_input(label, placeholder=el.get("placeholder", ""), key=name)
            responses[name] = val

        elif etype == "comment":
            val = st.text_area(
                label,
                placeholder=el.get("placeholder", ""),
                height=el.get("rows", 3) * 30,
                key=name,
            )
            responses[name] = val

        elif etype == "radiogroup":
            choices = el.get("choices", [])
            val = st.radio(label, choices, key=name)
            responses[name] = val

        elif etype == "checkbox":
            choices = el.get("choices", [])
            val = st.multiselect(label, choices, key=name)
            responses[name] = val

        elif etype == "dropdown":
            choices = el.get("choices", [])
            val = st.selectbox(label, [""] + choices, key=name)
            responses[name] = val if val else None

        elif etype == "rating":
            lo = el.get("rateMin", 1)
            hi = el.get("rateMax", 5)
            val = st.slider(label, min_value=lo, max_value=hi, value=lo, key=name)
            responses[name] = val

        elif etype == "boolean":
            val = st.checkbox(label, key=name)
            responses[name] = val

        else:
            val = st.text_input(label, key=name)
            responses[name] = val

    # Navigation
    col_prev, col_next, col_save, col_submit = st.columns(4)
    with col_prev:
        if st.session_state.current_page > 0 and st.button("Previous"):
            st.session_state.current_page -= 1
            st.rerun()
    with col_next:
        if st.session_state.current_page < total_pages - 1 and st.button("Next"):
            st.session_state.current_page += 1
            st.rerun()
    with col_save:
        if st.button("Save as JSON"):
            out = json.dumps(responses, indent=2)
            st.download_button(
                "Download JSON",
                data=out,
                file_name="form_responses.json",
                mime="application/json",
            )
    with col_submit:
        if st.button(form_def.get("completeText", "Submit")):
            errs = validate_responses(form_def, responses)
            if errs:
                for e in errs:
                    st.error(e)
            else:
                try:
                    resp = requests.post(
                        f"{api_url}/submit",
                        json={"form_id": form_def.get("title", "default"), "responses": responses},
                        timeout=10,
                    )
                    resp.raise_for_status()
                    st.success(f"Submitted! ID: {resp.json()['id']}")
                except Exception as exc:
                    st.error(f"Submission failed: {exc}")

# ===================================================================
# MODE 2 — Tiny in-browser WebGPU LLM chat
# ===================================================================
else:
    st.title("WebGPU LLM Chat")
    st.markdown(
        "This loads a small language model **directly in your browser** via WebGPU "
        "using [web-llm](https://github.com/mlc-ai/web-llm). No server needed for inference."
    )

    # Embed the WebGPU chat widget via an HTML component
    webgpu_html = """
    <div id="chat-container" style="font-family:sans-serif; max-width:680px;">
      <div id="status" style="padding:8px;background:#f0f0f0;border-radius:4px;margin-bottom:8px;">
        Loading model… (requires WebGPU-capable browser)
      </div>
      <div id="messages" style="height:350px;overflow-y:auto;border:1px solid #ccc;
           border-radius:4px;padding:8px;margin-bottom:8px;background:#fafafa;"></div>
      <div style="display:flex;gap:6px;">
        <input id="user-input" type="text" placeholder="Type a message…"
               style="flex:1;padding:8px;border:1px solid #ccc;border-radius:4px;"
               onkeydown="if(event.key==='Enter')sendMsg()"/>
        <button onclick="sendMsg()"
                style="padding:8px 16px;border:none;background:#4A90D9;color:#fff;
                       border-radius:4px;cursor:pointer;">Send</button>
      </div>
    </div>

    <script type="module">
      import * as webllm from "https://esm.run/@anthropic-ai/web-llm@0.2.76";

      const statusEl  = document.getElementById("status");
      const msgsEl    = document.getElementById("messages");

      let engine = null;

      function addMsg(role, text) {
        const d = document.createElement("div");
        d.style.marginBottom = "6px";
        d.innerHTML = "<strong>" + role + ":</strong> " + text;
        msgsEl.appendChild(d);
        msgsEl.scrollTop = msgsEl.scrollHeight;
      }

      async function init() {
        try {
          statusEl.textContent = "Checking WebGPU support…";
          if (!navigator.gpu) {
            statusEl.textContent = "WebGPU not supported in this browser. Try Chrome 113+.";
            return;
          }
          statusEl.textContent = "Downloading & compiling model (first load may take a minute)…";
          engine = await webllm.CreateMLCEngine("SmolLM2-135M-Instruct-q4f16_1-MLC", {
            initProgressCallback: (p) => {
              statusEl.textContent = p.text || "Loading…";
            },
          });
          statusEl.textContent = "Model ready! Type a message below.";
        } catch(e) {
          statusEl.textContent = "Error loading model: " + e.message;
          console.error(e);
        }
      }

      window.sendMsg = async function() {
        const inp = document.getElementById("user-input");
        const text = inp.value.trim();
        if (!text || !engine) return;
        inp.value = "";
        addMsg("You", text);
        statusEl.textContent = "Generating…";
        try {
          const reply = await engine.chat.completions.create({
            messages: [{role:"user", content: text}],
            max_tokens: 256,
          });
          const content = reply.choices[0].message.content;
          addMsg("LLM", content);
          statusEl.textContent = "Model ready!";
        } catch(e) {
          addMsg("Error", e.message);
          statusEl.textContent = "Error during generation.";
        }
      };

      init();
    </script>
    """

    import streamlit.components.v1 as components
    components.html(webgpu_html, height=520)

    st.info(
        "The chat runs a ~135 M-parameter model entirely in your browser via WebGPU. "
        "No data leaves your machine during inference."
    )
