from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src_consola.console import ConsolaPoliMarket


def main() -> None:
    app = ConsolaPoliMarket.desde_db_compartida()
    app.ejecutar()


if __name__ == "__main__":
    main()

