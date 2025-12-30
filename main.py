import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sqlite3
from zoneinfo import ZoneInfo


# LOGIN SISTEM
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 Login Sistem Parkir")

    with st.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        if user.strip() == "admin" and pwd.strip() == "123":
            st.session_state.login = True
            st.success("Login berhasil")
            st.rerun()
        else:
            st.error("Username atau password salah")

    st.stop()


st.set_page_config(
    page_title="Sistem Parkir",
    page_icon="🚗",
    layout="wide"
)

DB_FILE = "parkir.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS parkir (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomor_kendaraan TEXT,
    jenis_kendaraan TEXT,
    waktu_masuk TEXT,
    waktu_keluar TEXT,
    durasi_jam INTEGER,
    biaya INTEGER,
    status TEXT
)
""")
conn.commit()


# FUNGSI BANTUAN
def load_data():
    try:
        query = """
        SELECT 
            nomor_kendaraan,
            jenis_kendaraan,
            waktu_masuk,
            waktu_keluar,
            durasi_jam,
            biaya,
            status
        FROM parkir
        """
        df = pd.read_sql(query, conn)

        df.columns = [
            "Nomor Kendaraan",
            "Jenis Kendaraan",
            "Waktu Masuk",
            "Waktu Keluar",
            "Durasi (Jam)",
            "Biaya",
            "Status"
        ]

    except:
        df = pd.DataFrame(columns=[
            "Nomor Kendaraan",
            "Jenis Kendaraan",
            "Waktu Masuk",
            "Waktu Keluar",
            "Durasi (Jam)",
            "Biaya",
            "Status"
        ])

    return df

def save_data(df):
    cursor.execute("DELETE FROM parkir")
    conn.commit()

    for _, row in df.iterrows():
        cursor.execute("""
        INSERT INTO parkir (
            nomor_kendaraan,
            jenis_kendaraan,
            waktu_masuk,
            waktu_keluar,
            durasi_jam,
            biaya,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            row["Nomor Kendaraan"],
            row["Jenis Kendaraan"],
            row["Waktu Masuk"],
            row["Waktu Keluar"],
            int(row["Durasi (Jam)"]),
            int(row["Biaya"]),
            row["Status"]
        ))

    conn.commit()

def tampilkan_tabel(df):
    df_tampil = df.copy()
    df_tampil.index = df_tampil.index + 1
    df_tampil.index.name = "No"
    return df_tampil

# SIDEBAR
st.sidebar.title("🚗 Sistem Parkir")
menu = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Parkir Masuk", "Parkir Keluar", "Data Parkir"]
)

# Tarif parkir
st.sidebar.subheader("⚙️ Tarif Parkir")
tarif_motor = st.sidebar.number_input("Motor / Jam", 1000, 10000, 2000)
tarif_mobil = st.sidebar.number_input("Mobil / Jam", 2000, 20000, 4000)

st.sidebar.divider()
if st.sidebar.button("🚪 Logout"):
    st.session_state.login = False
    st.rerun()

df = load_data()

# DASHBOARD
if menu == "Dashboard":
    st.title("📊 Dashboard Parkir")

    total_parkir = len(df)
    sedang_parkir = len(df[df["Status"] == "Masuk"])
    total_pendapatan = df["Biaya"].sum() if not df.empty else 0


    col1, col2, col3 = st.columns(3)
    col1.metric("🚗 Total Kendaraan", total_parkir)
    col2.metric("🅿️ Sedang Parkir", sedang_parkir)
    col3.metric("💰 Pendapatan", f"Rp {int(total_pendapatan):,}")

    st.subheader("📈 Data Parkir Terbaru")
    st.dataframe(tampilkan_tabel(df.tail(5)), use_container_width=True)

# PARKIR MASUK
elif menu == "Parkir Masuk":
    st.title("🅿️ Parkir Masuk")

    with st.form("form_masuk"):
        nomor = st.text_input("Nomor Kendaraan")
        jenis = st.selectbox("Jenis Kendaraan", ["Motor", "Mobil"])
        submit = st.form_submit_button("Simpan")

    if submit:
      nomor = nomor.upper().strip()

      if nomor == "":
        st.error("Nomor kendaraan wajib diisi")
      else:
        # cek plat ganda
        cek = df[
            (df["Nomor Kendaraan"] == nomor) &
            (df["Status"] == "Masuk")
        ]

        if not cek.empty:
            st.error("❌ Kendaraan dengan nomor ini masih sedang parkir!")
        else:
            waktu_masuk = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S")

            new_data = {
                "Nomor Kendaraan": nomor,
                "Jenis Kendaraan": jenis,
                "Waktu Masuk": waktu_masuk,
                "Waktu Keluar": "",
                "Durasi (Jam)": 0,
                "Biaya": 0,
                "Status": "Masuk"
            }

            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            save_data(df)

            st.success("✅ Parkir berhasil dicatat")
            st.info(f"🕒 Waktu Masuk: {waktu_masuk}")


# PARKIR KELUAR
elif menu == "Parkir Keluar":
    st.title("🚙 Parkir Keluar")

    kendaraan_masuk = (
        df[df["Status"] == "Masuk"]["Nomor Kendaraan"]
        .dropna()
        .unique()
        .tolist()
    )

    if not kendaraan_masuk:
        st.warning("Tidak ada kendaraan yang sedang parkir")
    else:
        nomor = st.selectbox("Pilih Nomor Kendaraan", kendaraan_masuk)

        if st.button("Proses Keluar"):
            data_keluar = df[
                (df["Nomor Kendaraan"] == nomor) &
                (df["Status"] == "Masuk")
            ]

            if data_keluar.empty:
                st.error("❌ Data kendaraan tidak ditemukan atau sudah keluar")
                st.stop()

            idx = data_keluar.index[0]

            waktu_masuk = datetime.strptime(
                df.loc[idx, "Waktu Masuk"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=ZoneInfo("Asia/Jakarta"))
            waktu_keluar = datetime.now(ZoneInfo("Asia/Jakarta"))


        
            # LOGIKA DURASI
            selisih_detik = int((waktu_keluar - waktu_masuk).total_seconds())
            jam = selisih_detik // 3600
            menit = (selisih_detik % 3600) // 60

            if jam == 0:
                durasi_text = f"{menit} menit"
            else:
                durasi_text = f"{jam} jam {menit} menit"

            durasi_jam_biaya = jam + (1 if menit > 0 else 0)
            durasi_jam_biaya = max(1, durasi_jam_biaya)

            jenis = df.loc[idx, "Jenis Kendaraan"]
            tarif = tarif_motor if jenis == "Motor" else tarif_mobil
            biaya = durasi_jam_biaya * tarif

            df.loc[idx, "Waktu Keluar"] = waktu_keluar.strftime("%Y-%m-%d %H:%M:%S")
            df.loc[idx, "Durasi (Jam)"] = durasi_jam_biaya
            df.loc[idx, "Biaya"] = biaya
            df.loc[idx, "Status"] = "Keluar"

            save_data(df)

            st.success("✅ Parkir selesai")

            struk = f"""
=========================
       STRUK PARKIR
=========================
Nomor Kendaraan : {nomor}
Jenis Kendaraan : {jenis}

Waktu Masuk  : {waktu_masuk.strftime('%Y-%m-%d %H:%M:%S')}
Waktu Keluar : {waktu_keluar.strftime('%Y-%m-%d %H:%M:%S')}
Durasi       : {durasi_text}

Tarif / Jam  : Rp {tarif:,}
-------------------------
Total Bayar  : Rp {biaya:,}
=========================
   TERIMA KASIH
"""
            st.code(struk, language="text")


# DATA PARKIR + REKAP
elif menu == "Data Parkir":
    st.title("📋 Data & Rekap Parkir")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Data Detail",
        "📅 Rekap Harian",
        "📆 Rekap Mingguan",
        "🗓️ Rekap Bulanan",
        "🗑️ Hapus Data"
    ])

    # TAB 1 - DATA DETAIL
    with tab1:
        st.subheader("📋 Data Parkir Lengkap")
        st.dataframe(tampilkan_tabel(df), use_container_width=True)


    # DATA YANG SUDAH KELUAR
    df_keluar = df[df["Status"] == "Keluar"].copy()


    # TAB 2,3,4 - DATA REKAP
    if not df_keluar.empty:
        df_keluar["Waktu Keluar"] = pd.to_datetime(df_keluar["Waktu Keluar"])

        # TAB 2 - REKAP HARIAN
        with tab2:
            st.subheader("📅 Rekap Harian")
            df_keluar["Tanggal"] = df_keluar["Waktu Keluar"].dt.date

            rekap_harian = df_keluar.groupby("Tanggal").agg(
                Jumlah_Kendaraan=("Nomor Kendaraan", "count"),
                Total_Pendapatan=("Biaya", "sum")
            ).reset_index()

            st.dataframe(tampilkan_tabel(rekap_harian), use_container_width=True)

        # TAB 3 - REKAP MINGGUAN
        with tab3:
            st.subheader("📆 Rekap Mingguan")
            df_keluar["Tahun"] = df_keluar["Waktu Keluar"].dt.year
            df_keluar["Minggu"] = df_keluar["Waktu Keluar"].dt.isocalendar().week

            rekap_mingguan = df_keluar.groupby(
                ["Tahun", "Minggu"]
            ).agg(
                Jumlah_Kendaraan=("Nomor Kendaraan", "count"),
                Total_Pendapatan=("Biaya", "sum")
            ).reset_index()

            st.dataframe(tampilkan_tabel(rekap_mingguan), use_container_width=True)

        # TAB 4 - REKAP BULANAN
        with tab4:
            st.subheader("🗓️ Rekap Bulanan")
            df_keluar["Bulan"] = df_keluar["Waktu Keluar"].dt.month_name()
            df_keluar["Tahun"] = df_keluar["Waktu Keluar"].dt.year

            rekap_bulanan = df_keluar.groupby(
                ["Tahun", "Bulan"]
            ).agg(
                Jumlah_Kendaraan=("Nomor Kendaraan", "count"),
                Total_Pendapatan=("Biaya", "sum")
            ).reset_index()

            st.dataframe(tampilkan_tabel(rekap_bulanan), use_container_width=True)

    else:
        with tab2:
            st.info("Belum ada data parkir yang selesai.")
        with tab3:
            st.info("Belum ada data parkir yang selesai.")
        with tab4:
            st.info("Belum ada data parkir yang selesai.")


    # TAB 5 - HAPUS DATA
    with tab5:
        st.subheader("🗑️ Hapus Data Parkir")

        # Notifikasi sukses
        if "hapus_sukses" in st.session_state:
            st.success(
                f"✅ Data kendaraan {st.session_state['hapus_sukses']} berhasil dihapus"
            )
            del st.session_state["hapus_sukses"]

        if df.empty:
            st.info("Tidak ada data untuk dihapus")
        else:
            pilihan = df["Nomor Kendaraan"].dropna().unique().tolist()

            nomor_hapus = st.selectbox(
                "Pilih Nomor Kendaraan",
                pilihan
            )

            data_terpilih = df[df["Nomor Kendaraan"] == nomor_hapus]

            st.write("📄 Data Kendaraan:")
            st.dataframe(
                tampilkan_tabel(data_terpilih),
                use_container_width=True
            )

            status_kendaraan = data_terpilih.iloc[0]["Status"]

            # 🚫 diLarangan hapus jika masih Masuk
            if status_kendaraan == "Masuk":
                st.error(
                    "🚫 Kendaraan masih berstatus **MASUK**.\n\n"
                    "Silakan proses **KELUAR** terlebih dahulu."
                )
            else:
                st.warning("⚠️ Data yang dihapus tidak bisa dikembalikan!")
                konfirmasi = st.checkbox("Saya yakin ingin menghapus data ini")

                if st.button("🗑️ Hapus Data", disabled=not konfirmasi):
                    df = df[df["Nomor Kendaraan"] != nomor_hapus]
                    save_data(df)

                    st.session_state["hapus_sukses"] = nomor_hapus
                    st.rerun()

