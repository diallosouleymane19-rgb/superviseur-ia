import datetime

def generer_fec():
    filename = f"FEC_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("Journal\tDate\tCompte\tLibellé\tDébit\tCrédit\n")
        f.write("AC\t20240101\t606\tAchat fournitures\t100.00\t0.00\n")

    return filename

