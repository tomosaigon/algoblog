from typing import Literal
from pyteal import *
from beaker import *
from beaker.lib.storage import Mapping, List
from beaker.application import get_method_signature
from algosdk.encoding import decode_address, encode_address

from pprint import pprint
import argparse
import time

Nickname = abi.StaticBytes[Literal[8]]
Username = abi.StaticBytes[Literal[15]]
Timestamp = abi.Uint64
# Timestamp = abi.StaticBytes[Literal[8]]

def _nick(bs):
    return bs.ljust(8, b'\x00')

def _username(bs):
    return bs.ljust(15, b'\x00')

MAX_USERS = 20
MAX_TWEETS = 100

class UserRecord(abi.NamedTuple):
    nick: abi.Field[Nickname]
    username: abi.Field[Username]
    app_id: abi.Field[abi.Uint64]
    addr: abi.Field[abi.Address] # A 32-byte Algorand address. This is an alias for abi.StaticArray[abi.Byte, Literal[32]].
    canonical_uri: abi.Field[abi.String]

class AlgoBlogRegistry(Application):
    registry = Mapping(abi.String, UserRecord)
    usernames = List(Nickname, MAX_USERS)

    @external #(authorize=Authorize.only(Global.creator_address()))
    def bootstrap(
        self,
        *,
        output: abi.String,
    ):
        return Seq(
            App.box_put(Bytes("user_count"), Bytes((0).to_bytes(length=1, byteorder='big'))),
            Pop(self.usernames.create()),
            output.set(Bytes("booted")),
        )
    
    @external
    def register(self, nick: Nickname, username: Username, app_id: abi.Uint64, app_addr: abi.Address, canonical_uri: abi.String, *, output: abi.String):
        # TODO check existing nicks
        return Seq(
            (user := UserRecord()).set(nick, username, app_id, app_addr, canonical_uri),
            self.registry[nick.get()].set(user),
            user_count := App.box_get(Bytes("user_count")),
            Assert(user_count.hasValue()),
            self.usernames[Btoi(user_count.value())].set(nick),
            App.box_put(Bytes("user_count"), SetByte(Bytes("_"), Int(0), Int(1) + Btoi(user_count.value()))),
            output.set(username.get())
        )

    @external 
    def get_user(self, nick: Nickname, *, output: UserRecord):
        return Seq(
            self.registry[nick.get()].store_into(output)
        )
    
    @external 
    def get_nick_by_idx(self, idx: abi.Uint8, *, output: Nickname):
        return Seq(
            self.usernames[idx.get()].store_into(output)
        )
    
def deploy_registry():
    deploy = 1

    if deploy:
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlogRegistry(version=8),
            signer=sandbox.get_accounts().pop().signer,
        )

        app_id, app_addr, txid = app_client.create()
        print(
            f"""Deployed app in txid {txid}
            App ID: {app_id} 
            Address: {app_addr} 
        """
        )
    else:
        app_addr = 'NCYBSXIYSDOIJ5ZB2A7B7UJXKAWJJN5XRUK5PQ26L3MFS5S6FLVZJR4FOM'
        app_id = 1217
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlogRegistry(version=8),
            app_id=app_id,
            signer=sandbox.get_accounts().pop().signer,
        )

    app_client.fund(517000, app_addr)
    boxen = lambda x: [[app_client.app_id, name] for name in x]

    result = app_client.call(AlgoBlogRegistry.bootstrap,
                              boxes=boxen(['user_count', 'usernames']))
    print("bootstrap result: ", result.return_value) 

    return app_client

def regdemo():
    app_client = deploy_registry()
    boxen = lambda x: [[app_client.app_id, name] for name in x]
    someappid = 1304
    someaddr = decode_address(app_client.app_addr)

    # tomo = b"tomo\x00\x00\x00\x00" # 8 byte nickname
    tomo8 = _nick(b'tomo')
    tomo15 = _username(b'tomo')
    result = app_client.call(AlgoBlogRegistry.register, boxes=boxen(['user_count', 'usernames', tomo8]),
                              app_id=someappid,
                              nick=tomo8, username=tomo15, app_addr=someaddr, canonical_uri="uri://example")
    print("register result: ", result.return_value) 
    result = app_client.call(AlgoBlogRegistry.get_user, boxes=boxen([tomo8]) , nick=tomo8)
    pprint(vars(result))
    print("get_user: ", result.return_value)
    print(''.join([chr(x) for x in result.return_value[0]]))

    result = app_client.call(AlgoBlogRegistry.get_nick_by_idx, boxes=boxen(['usernames']) , idx=0)
    # pprint(vars(result))
    print("get_nick_by_idx ", ''.join([chr(x) for x in result.return_value]))

    result = app_client.call(AlgoBlogRegistry.register, boxes=boxen(['user_count', 'usernames', b'root1234']),
                              nick=_nick(b'root1234'), username=_username(b"root1234"),
                              app_id=someappid,
                              app_addr=someaddr, canonical_uri="uri://example")
    result = app_client.call(AlgoBlogRegistry.register, boxes=boxen(['user_count', 'usernames', b'satoshi ']),
                              app_id=someappid,
                              nick=b'satoshi ', username=_username(b"satoshi"),  app_addr=someaddr, canonical_uri="uri://example")
    result = app_client.call(AlgoBlogRegistry.get_user, boxes=boxen([b'satoshi ']) , nick=b'satoshi ')
    print("get_user: ", result.return_value)
    result = app_client.call(AlgoBlogRegistry.get_nick_by_idx, boxes=boxen(['usernames']) , idx=2)
    print("get_nick_by_idx ", ''.join([chr(x) for x in result.return_value]))


class Checker(Application):
    @external
    def one(self, *, output: abi.Uint8):
        return Seq(
            output.set(Int(1))
        )

    @external
    def oneself(self, *, output: abi.String):
        return Seq(
            InnerTxnBuilder.ExecuteMethodCall(
                app_id=Int(1304),
                method_signature="one()uint8",
                args=[],
            ),
            output.set("ok")
        )
    
    @external
    def nick_matches(self, nick: Nickname, app_id: abi.Uint64, *, output: Nickname):
        # pushbytes 0x4bac4e0b // "nick_matches(byte[8],uint64,string)void"
        return Seq(
            InnerTxnBuilder.ExecuteMethodCall(
                app_id=app_id.get(),
                # method_signature="get_nick()uint8",
                method_signature=get_method_signature(AlgoBlog.get_nick),
                args=[],
            ),
            # Assert(BytesEq(retval, nick.get())),
            Assert(BytesEq(nick.get(), Suffix(InnerTxn.last_log(), Int(4)))),
            output.decode(Suffix(InnerTxn.last_log(), Int(4)))
        )    

def deploy_checker():
    deploy = 1

    if deploy:
        # Create an Application client
        app_client = client.ApplicationClient(
            # Get sandbox algod client
            client=sandbox.get_algod_client(),
            # Instantiate app with the program version (default is MAX_TEAL_VERSION)
            app=Checker(version=8),
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )

        # Deploy the app on-chain
        app_id, app_addr, txid = app_client.create()
        print(
            f"""Deployed app in txid {txid}
            App ID: {app_id} 
            Address: {app_addr} 
        """
        )
    else:
        app_addr = 'IKFUUZDNRXCZSVEWGFKEGSNHXBYXFFBMYRQP6X3EOTEAD4L3NHWCSSFKNQ'
        app_client = client.ApplicationClient(
            # Get sandbox algod client
            client=sandbox.get_algod_client(),
            # Instantiate app with the program version (default is MAX_TEAL_VERSION)
            app=Checker(version=8),
            app_id=1191,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )

    boxen = lambda x: [[app_client.app_id, name] for name in x]
    app_client.fund(517000, app_addr) # app_client.fund(108100, app_addr)
    return app_client

def demo_checker():
    app_client = deploy_checker()
    boxen = lambda x: [[app_client.app_id, name] for name in x]

    result = app_client.call(Checker.oneself, foreign_apps=[1304])
    print("check oneself: ", result.return_value) 

    result = app_client.call(Checker.nick_matches, 
                             foreign_apps=[1391],
                             boxes=[[1391, "nick"]],
                            #  boxes=boxen(["username", "nick"]),
                             nick=_nick(b'tomo'), app_id=1391
                            )
    print("nick_matches: ", result.return_value) 

# Create a class, subclassing Application from beaker
class AlgoBlog(Application):
    timestamps = List(Timestamp, MAX_TWEETS)

    @external
    def init(self, nick: Nickname, username: Username, *, output: abi.String):
        return Seq(
            Pop(self.timestamps.create()),
            App.box_put(Bytes("nick"), nick.get()),
            App.box_put(Bytes("username"), username.get()),
            output.set(username.get())
        )
    
    @external
    def get_nick(self, *, output: Nickname):
        return Seq(
            nick := App.box_get(Bytes("nick")),
            Assert(nick.hasValue()),
            output.set(nick.value())
        )
    
    @external
    def idLast_reset(self, *, output: abi.String):
        return Seq(
            App.box_put(Bytes("idLast"), Bytes((0).to_bytes(length=1, byteorder='big'))),
            last := App.box_get(Bytes("idLast")),
            Assert(last.hasValue()),
            output.set(last.value())
        )
     
    @external
    def idLast_inc(self, *, output: abi.String):
        return Seq(
            last := App.box_get(Bytes("idLast")),
            Assert(last.hasValue()),
            App.box_put(Bytes("idLast"), SetByte(Bytes("_"), Int(0), (Int(1) + Btoi(last.value())) % Int(10) ) ) ,
            output.set(SetByte(Bytes("id:?"), Int(3), Int(ord('0')) + (Int(1) + Btoi(last.value())) % Int(10)))
        )   

    @external #(read_only=True) doesn't work
    def get_idLast(self, *, output: abi.String):
        return Seq(
            last := App.box_get(Bytes("idLast")),
            Assert(last.hasValue()),
            output.set(SetByte(Bytes("id:?"), Int(3), Int(ord('0')) + Btoi(last.value()) )) #% Int(10)))
        )
    
    @external
    def get_tweet(self, id: abi.String, *, output: abi.String):
        return Seq(
            tweet := App.box_get(Concat(Bytes("id:"), id.get())),
            Assert(tweet.hasValue()),
            output.set(tweet.value())
        )

    @external
    def get_tweet_timestamp(self, idx: abi.Uint64, *, output: Timestamp):
        return Seq(
            # NOT self.timestamps[idx.get()].store_into(output)
            output.set(Btoi(self.timestamps[idx.get()]))
            # output.set(App.globalGet(Bytes("tstamp"))),
        )

    @external
    def post_tweet(self, tstamp: Timestamp, tweet: abi.String, *, output: abi.String):
        # TODO new box instead of box_put
        return Seq(
            last := App.box_get(Bytes("idLast")),
            Assert(last.hasValue()),
            # (now := Global.latest_timestamp()),
            # Assert(Gt(now, tstamp.get())),
            # Assert(now < tstamp.get()),
            Assert(tstamp.get() > Global.latest_timestamp()),

            # FAILS: AttributeError: 'Global' object has no attribute 'encode'
            # self.timestamps[Btoi(last.value())].set((Bytes('12345678'))),
            # self.timestamps[Btoi(last.value())].set(now),
            # self.timestamps[Btoi(last.value())].set(foo), # foo: abi.Uint64 works
            self.timestamps[Btoi(last.value())].set(tstamp), # idx = id - 1

            # need storage when creating contract
            # App.globalPut(Bytes("tstamp"), Global.latest_timestamp()),
            # App.globalPut is PyTeal code, and ApplicationStateValue is its equivalent in Beaker. Additionally, you would want to use AccountStateValue in Beaker rather than PyTeal's App.localPut.
            App.box_put(Bytes("idLast"), SetByte(Bytes("_"), Int(0), (Int(1) + Btoi(last.value())) % Int(10) ) ) ,
            App.box_put(SetByte(Bytes("id:?"), Int(3), Int(0x30) + (Int(1) + Btoi(last.value())) % Int(10)), tweet.get()),
            output.set(SetByte(Bytes("id:?"), Int(3), Int(0x30) + (Int(1) + Btoi(last.value())) % Int(10)))
        )

def deploy_blog():
    deploy = 1

    if deploy:
        # testnet, no token: https://testnet.algoexplorer.io/api-dev/v2

        # Create an Application client
        app_client = client.ApplicationClient(
            # Get sandbox algod client
            client=sandbox.get_algod_client(),
            # Instantiate app with the program version (default is MAX_TEAL_VERSION)
            app=AlgoBlog(version=8),
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )

        # Deploy the app on-chain
        app_id, app_addr, txid = app_client.create()
        print(
            f"""Deployed app in txid {txid}
            App ID: {app_id} 
            Address: {app_addr} 
        """
        )
    else:
        app_addr = 'IKFUUZDNRXCZSVEWGFKEGSNHXBYXFFBMYRQP6X3EOTEAD4L3NHWCSSFKNQ'
        app_client = client.ApplicationClient(
            # Get sandbox algod client
            client=sandbox.get_algod_client(),
            # Instantiate app with the program version (default is MAX_TEAL_VERSION)
            app=AlgoBlog(version=8),
            app_id=1191,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )

    boxen = lambda x: [[app_client.app_id, name] for name in x]
    app_client.fund(517000, app_addr) # app_client.fund(108100, app_addr)

    return app_client

def demo():
    app_client = deploy_blog()
    boxen = lambda x: [[app_client.app_id, name] for name in x]

    result = app_client.call(AlgoBlog.init, boxes=boxen(["username", "nick"]),
                             nick=_nick(b'tomo'), username=_username(b'tomo'))
    print("created account: ", result.return_value) 
    result = app_client.call(AlgoBlog.get_nick, boxes=boxen(["nick"]))
    print("Confirm nick set: ", result.return_value)

    result = app_client.call(AlgoBlog.idLast_reset, boxes=boxen(["idLast"]))
    pprint(vars(result))
    # result = app_client.call(AlgoBlog.idLast_inc, boxes=[[app_client.app_id, "idLast"]])
    # pprint(vars(result))

    result = app_client.call(AlgoBlog.post_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:1"]], tweet="First test message")
    print("Resulting id of 1st tweet: ", result.return_value)

    result = app_client.call(AlgoBlog.get_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:1"]], id="1")
    print("tweet 1: ", result.return_value) 

    result = app_client.call(AlgoBlog.get_idLast, boxes=[[app_client.app_id, "idLast"]])
    print("updated idLast nonce: ", result.return_value)
    id = result.return_value.split(':')[1]
    idNext = int(id) + 1
    print("next: ")
    pprint(idNext)

    result = app_client.call(AlgoBlog.post_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(idNext)]], tweet="Second tweet")
    result = app_client.call(AlgoBlog.get_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(idNext)]], id=str(idNext))
    print("tweet 2: ", result.return_value)

    result = app_client.call(AlgoBlog.get_idLast, boxes=[[app_client.app_id, "idLast"]])
    id = result.return_value.split(':')[1]
    idNext = int(id) + 1
    result = app_client.call(AlgoBlog.post_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(idNext)]], tweet="This is just another example.")
    result = app_client.call(AlgoBlog.get_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(idNext)]], id=str(idNext))
    print(result.return_value)

    tweets = [
        'No one is born hating another person because of the color of his skin or his background or his religion.',
        "Next I'm buying Coca-Cola to put the cocaine back in",
        'yes, please do enlighten me. email me at smalldickenergy@getalife.com',
        "It's a new day in America.",
        "this is what happens when you don’t recycle your pizza boxes",
        "I hope that even my worst critics remain on Twitter, because that is what free speech means",
    ]
    for tweet in tweets:
        idNext = idNext + 1
        result = app_client.call(AlgoBlog.post_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(idNext)]], tweet=tweet)
        result = app_client.call(AlgoBlog.get_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(idNext)]], id=str(idNext))
        print("tweeted: ", result.return_value)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Commands for AlgoBlog and AlgoBlogRegistry")
    parser.add_argument("function", choices=["deploy_registry", "deploy_blog", "init_blog", "tweet", "lastId", "get_tweet", "register"], help="Commands")
    parser.add_argument("--app_id", type=int, help="App ID to call")
    parser.add_argument("--blog_app_id", type=int, help="App ID of AlgoBlog to register") 
    parser.add_argument("--post_id", type=int, help="Post ID")
    parser.add_argument("--txt", type=str, help="Tweet text")
    parser.add_argument("--nick", type=str, help="Nick (to 8 bytes)")
    parser.add_argument("--username", type=str, help="Username (to 15 bytes)")
    args = parser.parse_args()
    if args.function == "deploy_registry":
        app_client = deploy_registry()
        print("- app_id: ", app_client.app_id)
    elif args.function == "deploy_blog":
        app_client = deploy_blog()
        print("- app_id: ", app_client.app_id)
        print("Next you should: init_blog --app_id", app_client.app_id)

    elif args.function == 'init_blog':
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlog(version=8),
            app_id=args.app_id,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )
        boxen = lambda x: [[app_client.app_id, name] for name in x]
        result = app_client.call(AlgoBlog.init, boxes=boxen(["username", "nick", "timestamps"]),
                            nick=_nick(b'tomo'), username=_username(b'tomo'))
        print("created account: ", result.return_value) 
        result = app_client.call(AlgoBlog.get_nick, boxes=boxen(["nick"]))
        print("Confirm nick set: ", result.return_value)
        result = app_client.call(AlgoBlog.idLast_reset, boxes=boxen(["idLast"]))
        print("Next you should: tweet --app_id {} --txt '1st tweet' --post_id 1".format(app_client.app_id))

    elif args.function == 'lastId':
        # curl -s http://localhost:4001/v2/applications/1501/box?application-id=1501\&name=str:idLast -H "X-Algo-API-Token: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" | jq -r .value | base64 -d | hexdump
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlog(version=8),
            app_id=args.app_id,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )
        boxen = lambda x: [[app_client.app_id, name] for name in x]
        # result = app_client.call(AlgoBlog.idLast_reset, boxes=boxen(["idLast"]))
        result = app_client.call(AlgoBlog.get_idLast, boxes=[[app_client.app_id, "idLast"]])
        print("updated idLast nonce: ", result.return_value)
        id = result.return_value.split(':')[1]
        idNext = int(id) + 1
        print("next: ", idNext)

    elif args.function == 'tweet':
        print("posting tweet:", args.post_id)
        if not args.post_id:
            raise Exception("no post_id")
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlog(version=8),
            app_id=args.app_id,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )
        boxen = lambda x: [[app_client.app_id, name] for name in x]
        result = app_client.call(AlgoBlog.post_tweet, boxes=boxen(["idLast", "id:" + str(args.post_id), "timestamps"]), tweet=args.txt, tstamp=int(time.time())+60)
        # result = app_client.call(AlgoBlog.post_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(args.post_id)]], tweet=args.txt)
        print("Resulting id tweet: ", result.return_value)
        print("Next you should: get_tweet --app_id {} --post_id 1".format(app_client.app_id))
    
    elif args.function == 'get_tweet':
        # curl -s http://localhost:4001/v2/applications/1501/box?application-id=1501\&name=str:id:1 -H "X-Algo-API-Token: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" | jq -r .value | base64 -d
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlog(version=8),
            app_id=args.app_id,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )
        boxen = lambda x: [[app_client.app_id, name] for name in x]
        result = app_client.call(AlgoBlog.get_tweet, boxes=[[app_client.app_id, "idLast"], [app_client.app_id, "id:" + str(args.post_id)]], id=str(args.post_id))
        print("tweet: ", result.return_value)
        result = app_client.call(AlgoBlog.get_tweet_timestamp, boxes=[[app_client.app_id, "timestamps"]], idx=0)
        # result = app_client.call(AlgoBlog.get_tweet_timestamp, boxes=[[app_client.app_id, "timestamps"]], idx=args.post_id)
        print("tweet tstamp: ", result.return_value)

    elif args.function == 'register':
        app_client = client.ApplicationClient(
            client=sandbox.get_algod_client(),
            app=AlgoBlogRegistry(version=8),
            app_id=args.app_id,
            # Get acct from sandbox and pass the signer
            signer=sandbox.get_accounts().pop().signer,
        )
        boxen = lambda x: [[app_client.app_id, name] for name in x]
        someaddr = decode_address(app_client.app_addr)

        result = app_client.call(AlgoBlogRegistry.register, 
                                 boxes=boxen(['user_count', 'usernames', _nick(args.nick.encode('ascii'))]),
                              app_id=args.blog_app_id,
                              nick=_nick(args.nick.encode('ascii')), username=_username(args.username.encode('ascii')), app_addr=someaddr, canonical_uri="uri://example")
        print("register result: ", result.return_value) 

    else:
        # demo()
        demo_checker()
        # regdemo()
