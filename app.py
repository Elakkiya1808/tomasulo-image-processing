import io
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from image_processor import load_image, process_image, image_to_png_bytes
from instruction_generator import generate_instructions, initialize_registers
from tomasulo import TomasuloSimulator
from baseline import run_sequential_baseline


st.set_page_config(
    page_title="Tomasulo Image Processing",
    page_icon="🖥️",
    layout="wide"
)

st.title("Tomasulo-Based Instruction Scheduling for Image Processing")
st.caption(
    "Real image filters + an educational Tomasulo-style scheduling simulation. "
    "The generated instruction trace represents tile-level arithmetic; it is not "
    "a trace extracted from Pillow or NumPy machine code."
)

with st.sidebar:
    st.header("Workload Configuration")
    operation = st.selectbox(
        "Image-processing operation",
        ["Grayscale", "Brightness", "Edge Detection", "Sharpen"]
    )
    brightness_factor = st.slider(
        "Brightness factor", 0.5, 2.0, 1.3, 0.1,
        disabled=(operation != "Brightness")
    )
    tile_count = st.slider(
        "Number of representative image tiles",
        min_value=1, max_value=100, value=16, step=1,
        help="More tiles create a longer instruction trace for scheduling analysis."
    )
    uploaded_file = st.file_uploader(
        "Upload an image",
        type=["png", "jpg", "jpeg", "bmp"]
    )
    run_button = st.button("Run scheduling experiment", type="primary")

if uploaded_file is None:
    st.info("Upload an image from the sidebar to start.")
    st.markdown(
        """
        **What you can investigate**
        - Independent instructions executing concurrently
        - RAW data dependencies and register renaming
        - Reservation-station and functional-unit availability
        - One-result-per-cycle Common Data Bus contention
        - Cycle counts compared with a serial baseline
        """
    )
    st.stop()

image = load_image(uploaded_file)
processed = process_image(image, operation, brightness_factor)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Original image")
    st.image(image, use_container_width=True)
with col2:
    st.subheader(f"Processed image: {operation}")
    st.image(processed, use_container_width=True)

st.download_button(
    "Download processed image",
    data=image_to_png_bytes(processed),
    file_name=f"{operation.lower().replace(' ', '_')}.png",
    mime="image/png"
)

st.divider()
st.header("Instruction scheduling and performance")

instructions = generate_instructions(operation, tile_count)
simulator = TomasuloSimulator(instructions)
initialize_registers(
    simulator, operation, tile_count,
    brightness_factor=brightness_factor, image=image
)
initial_registers = dict(simulator.registers)

if run_button:
    with st.spinner("Running the Tomasulo and baseline models..."):
        tom_result = simulator.run()
        baseline_result = run_sequential_baseline(
            instructions, initial_registers
        )
        st.session_state["experiment"] = {
            "operation": operation,
            "tile_count": tile_count,
            "tomasulo": tom_result,
            "baseline": baseline_result,
            "instructions": instructions
        }

experiment = st.session_state.get("experiment")
if not experiment:
    st.warning("Click **Run scheduling experiment** to generate the report.")
    st.stop()

if experiment["operation"] != operation or experiment["tile_count"] != tile_count:
    st.info("Settings changed. Click **Run scheduling experiment** to refresh the results.")
    st.stop()

tom = experiment["tomasulo"]
base = experiment["baseline"]
n_inst = len(experiment["instructions"])
speedup = base["cycles"] / tom["cycles"] if tom["cycles"] else 0
cycle_reduction = (1 - tom["cycles"] / base["cycles"]) * 100 if base["cycles"] else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Instructions", n_inst)
m2.metric("Tomasulo cycles", tom["cycles"])
m3.metric("Serial baseline cycles", base["cycles"])
m4.metric("Cycle-count ratio", f"{speedup:.2f}×")

st.caption(
    f"Compared with the serial reference, the Tomasulo model uses "
    f"{cycle_reduction:.1f}% fewer simulated cycles. This is a simulation result, "
    "not a measured CPU runtime speedup."
)

chart_col, detail_col = st.columns([1, 2])
with chart_col:
    st.subheader("Cycle-count comparison")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Serial baseline", "Tomasulo"], [base["cycles"], tom["cycles"]])
    ax.set_ylabel("Simulated cycles")
    ax.grid(axis="y", alpha=0.25)
    st.pyplot(fig)
with detail_col:
    st.subheader("Tomasulo instruction status")
    status_df = pd.DataFrame(tom["instructions"])
    st.dataframe(status_df, use_container_width=True, hide_index=True)

st.subheader("Execution timeline")
timeline_cols = ["Issue", "Execute Start", "Execute End", "Write Result"]
timeline = status_df[["Instruction ID", "Instruction"] + timeline_cols].melt(
    id_vars=["Instruction ID", "Instruction"],
    value_vars=timeline_cols,
    var_name="Stage",
    value_name="Cycle"
).dropna()

fig, ax = plt.subplots(figsize=(12, max(4, min(12, n_inst * 0.18))))
stage_order = {name: i for i, name in enumerate(timeline_cols)}
for _, row in timeline.iterrows():
    y = row["Instruction ID"]
    ax.scatter(row["Cycle"], y, s=18, label=row["Stage"])
ax.set_xlabel("Simulation cycle")
ax.set_ylabel("Instruction ID")
ax.set_title("Issue, execution, and result-writeback cycles")
ax.grid(True, alpha=0.25)
handles, labels = ax.get_legend_handles_labels()
unique = dict(zip(labels, handles))
if unique:
    ax.legend(unique.values(), unique.keys(), loc="best")
st.pyplot(fig)

# st.subheader("Reservation stations at simulation end")
# st.dataframe(pd.DataFrame(tom["stations"]), use_container_width=True, hide_index=True)

with st.expander("View Common Data Bus and scheduling event log"):
    st.dataframe(pd.DataFrame(tom["trace"]), use_container_width=True, hide_index=True)

with st.expander("View serial-baseline instruction table"):
    st.dataframe(pd.DataFrame(base["instructions"]), use_container_width=True, hide_index=True)

csv = status_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Tomasulo instruction report (CSV)",
    data=csv,
    file_name="tomasulo_instruction_report.csv",
    mime="text/csv"
)

st.markdown(
    """
    **Interpretation note:** the serial baseline deliberately prevents overlap,
    while the Tomasulo model allows independent operations to overlap subject to
    reservation stations, functional-unit limits, dependencies, and one CDB
    broadcast per cycle. The ratio is therefore a comparison with a serial
    reference—not a prediction of real hardware performance.
    """
)
