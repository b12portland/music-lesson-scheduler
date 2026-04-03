import argparse
from app import create_app

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed-initial-test-data",
        action="store_true",
        help="Populate the database with sample lessons for testing, then start the server.",
    )
    args = parser.parse_args()

    if args.seed_initial_test_data:
        from seed_dev_data import seed
        seed()

    app.run(host="127.0.0.1", port=5001, debug=True, use_reloader=False)
