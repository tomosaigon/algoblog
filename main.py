from pyteal import *
from beaker import *

from pprint import pprint

# Create a class, subclassing Application from beaker
class AlgoBlog(Application):
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

    @external
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
    def post_tweet(self, tweet: abi.String, *, output: abi.String):
        # TODO new box instead of box_put
        return Seq(
            last := App.box_get(Bytes("idLast")),
            Assert(last.hasValue()),
            App.box_put(Bytes("idLast"), SetByte(Bytes("_"), Int(0), (Int(1) + Btoi(last.value())) % Int(10) ) ) ,
            App.box_put(SetByte(Bytes("id:?"), Int(3), Int(0x30) + (Int(1) + Btoi(last.value())) % Int(10)), tweet.get()),
            output.set(SetByte(Bytes("id:?"), Int(3), Int(0x30) + (Int(1) + Btoi(last.value())) % Int(10)))
        )

def demo():
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

    app_client.fund(517000, app_addr) # app_client.fund(108100, app_addr)

    result = app_client.call(AlgoBlog.idLast_reset, boxes=[[app_client.app_id, "idLast"]])
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
    demo()
