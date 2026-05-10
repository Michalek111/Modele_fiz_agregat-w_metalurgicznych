import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Program PK", layout="wide")

st.title("Program PK - Obróbka wyników badań")

uploaded_file = st.file_uploader("Wczytaj plik CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(
            uploaded_file,
            encoding="cp1250",
            sep=";",
            decimal=","
        )
    except Exception as e:
        st.error("Nie udało się wczytać pliku CSV. Sprawdź, czy plik ma poprawny format.")
        st.exception(e)
        st.stop()

    if df.empty:
        st.error("Wczytany plik jest pusty.")
        st.stop()

    # Czyszczenie nazw kolumn
    df.columns = [
        col
        .split("(")[0]
        .replace("[uS/cm]", "")
        .strip()
        for col in df.columns
    ]

    st.subheader("Dane wejściowe")
    st.dataframe(df)

    if len(df) > 1:
        df = df.drop(index=1).reset_index(drop=True)

    df["Czas [s]"] = [i * 0.5 for i in range(len(df))]

    st.subheader("Dane po obróbce")
    st.dataframe(df)

    possible_channels = [
        col for col in df.columns
        if "PRZEWODNOSC" in col.upper() or "PRZEWODNOŚĆ" in col.upper()
    ]

    if not possible_channels:
        st.error("Nie znaleziono kolumn z przewodnością. Sprawdź, czy nazwy kolumn zawierają słowo PRZEWODNOSC lub PRZEWODNOŚĆ.")
        st.stop()

    display_names = {
        col: col.split("(")[0].strip()
        for col in possible_channels
    }

    st.write("Wybierz kanały:")

    selected_channels = []

    for original, clean in display_names.items():
        if st.checkbox(clean, value=True):
            selected_channels.append(original)

    st.subheader("Wykres przewodności")

    fig = go.Figure()

    for channel in selected_channels:
        clean_name = channel.split("(")[0].strip()

        fig.add_trace(
            go.Scatter(
                x=df["Czas [s]"],
                y=df[channel],
                mode="lines",
                name=clean_name
            )
        )

    fig.update_layout(
        title="Przewodność",
        xaxis_title="Czas [s]",
        yaxis_title="Przewodność [µS/cm]"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Przeliczenie na wartości bezwymiarowe")

    c_inf_method = st.radio(
        "Wybierz sposób wyznaczenia C∞",
        [
            "Ostatni pomiar",
            "Średnia z ostatnich X pomiarów"
        ]
    )

    x_measurements = 10

    if c_inf_method == "Średnia z ostatnich X pomiarów":
        x_measurements = st.number_input(
            "Podaj liczbę ostatnich pomiarów do średniej",
            min_value=1,
            max_value=len(df),
            value=10,
            step=1
        )

    df_dimensionless = df[["Czas [s]"]].copy()

    for channel in selected_channels:
        c0 = df[channel].iloc[0]

        if c_inf_method == "Ostatni pomiar":
            c_inf = df[channel].iloc[-1]
        else:
            c_inf = df[channel].tail(int(x_measurements)).mean()

        df_dimensionless[channel] = (df[channel] - c0) / (c_inf - c0)

    st.subheader("Dane bezwymiarowe")
    st.dataframe(df_dimensionless)

    st.subheader("Wykres wartości bezwymiarowych")

    fig2 = go.Figure()

    for channel in selected_channels:
        clean_name = channel.split("(")[0].strip()

        fig2.add_trace(
            go.Scatter(
                x=df_dimensionless["Czas [s]"],
                y=df_dimensionless[channel],
                mode="lines",
                name=clean_name
            )
        )

    fig2.add_hline(y=0.95, line_dash="dash", annotation_text="0.95")
    fig2.add_hline(y=1.05, line_dash="dash", annotation_text="1.05")

    fig2.update_layout(
        title="Stężenie bezwymiarowe",
        xaxis_title="Czas [s]",
        yaxis_title="Stężenie bezwymiarowe [-]"
    )


    st.subheader("Czasy mieszania")

    mixing_times = {}

    for channel in selected_channels:

        values = df_dimensionless[channel].values
        times = df_dimensionless["Czas [s]"].values

        mixing_time = None

        for i in range(len(values)):

            remaining_values = values[i:]

            if all((0.95 <= v <= 1.05) for v in remaining_values):
                mixing_time = times[i]
                break

        clean_name = (
            channel
            .split("(")[0]
            .replace("[uS/cm]", "")
            .strip()
        )

        if mixing_time is not None:
            mixing_times[clean_name] = mixing_time
            st.write(f"{clean_name}: {mixing_time:.1f} s")

            fig2.add_vline(
                x=mixing_time,
                line_dash="dot",
                annotation_text=f"{clean_name}: {mixing_time:.1f} s",
                annotation_position="top"
            )

        else:
            st.write(f"{clean_name}: nie osiągnięto stabilizacji")

    if mixing_times:

        max_channel = max(mixing_times, key=mixing_times.get)
        max_time = mixing_times[max_channel]

        st.success(
            f"Minimalny czas mieszania: {max_time:.1f} s ({max_channel})"
        )

    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Eksport danych")

    csv_data = df_dimensionless.to_csv(index=False, sep=";", decimal=",").encode("cp1250")

    st.download_button(
        label="Pobierz dane bezwymiarowe CSV",
        data=csv_data,
        file_name="dane_bezwymiarowe.csv",
        mime="text/csv"
    )