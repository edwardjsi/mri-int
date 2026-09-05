import json
from api.deps import get_db, get_current_client
from api.cai_saturday_review import get_saturday_review

def main():
    db_gen = get_db()
    conn = next(db_gen)
    try:
        client = {"id": 1} # or whatever get_current_client provides
        data = get_saturday_review(client=client, conn=conn)
        print(json.dumps(data, indent=2, default=str))
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

if __name__ == "__main__":
    main()
