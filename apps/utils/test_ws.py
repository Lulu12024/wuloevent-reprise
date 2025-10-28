# import argparse


# def parse_args():
#     parser = argparse.ArgumentParser(description="WebSocket Simple Dump Tool")
#     parser.add_argument("tid", metavar="transaction_id")
#     return parser.parse_args()


# def on_message(wsapp, message):

# def main():
#     args = parse_args()
#     print(args)
#     if not args.tid:
#         raise ValueError('Not Tid Entered')
#     wsapp = websocket.WebSocketApp(f'ws://127.0.0.1:8000/ws/transactions/{args.tid}/', on_message=on_message)
#     wsapp.run_forever()


# if __name__ == "__main__":
#     try:
#         main()
#     except Exception as e:
#         print(e)
