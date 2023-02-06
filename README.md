# algoblog
### Microblogging system on Algorand following the twtxt format

Introducing AlgoBlog, a new decentralized and censorship-resistant, microblogging platform built on Algorand. AlgoBlog is optimized for short tweets and is compatible with the TWTXT protocol. Anyone can create an account and unstoppably post tweets. The protocol has a registry system which allows communities to deploy their own registries if they wish to have more control over their own name space. Anyone can pull the code for the front end web server, which will run a gateway to publish any account to any existing TWTXT client. This enables any existing TWTXT client to follow an AlgoBlog user.

First, configure a connection to an API and make your wallet, private key accessible. You just need to export an algod token and mnemonic to your environment. You can also use a local sandbox without needing to configure an account. Then you just need to run the deploy blog command, then the init blog command. Now you're ready to start posting tweets. You can also register your account in the global registry to make it discoverable by others.

We found that the Purestake API works well and you will need an account to get an API key and connect to the test net endpoint: https://testnet-algorand.api.purestake.io/ps2

The global registry is deployed at this application ID: 157452421
Address: HOVIWJND6XJRI4FHAZGYXK4YV64NGPON6J36XMZY6IH4XP2DYFQMS3ECII

But anyone can deploy their own registries and use those instead. And accounts can be registered in multiple registries. So it's also impossible to stop accounts from listing and registering. The only way someone can cancel your account is by hacking your blockchain wallet. 

We use Beaker as a framework for developing this application, and this comes with data structures for representing maps and lists using boxes and this is how we represent the users in a registry. And by using boxes instead of global or local storage, we can dynamically add new storage for unlimited new tweets.

# blog
```
$ export ALGOD_TOKEN="your token"

$ export MNEMONIC="your seed phrase here"

$ python3 ./main.py deploy_blog
Deployed app in txid V37MYBUZ2YIBHJEMC7RMYBFY27SH44KUD47HLQ4U2TEYWOGIGUJA
            App ID: 156806034
            Address: P5YDHVQOBAA3OXBL4BOHAUKYBHXP5FSHDJHC64XETJLVI2PBPQ73WTS6VA

- app_id:  156806034
Next you should: init_blog --app_id 156806034

$ python3 ./main.py init_blog --app_id 156806034
created account:  tomo
Confirm nick set:  [116, 111, 109, 111, 0, 0, 0, 0]
Next you should: tweet --app_id 156806034 --txt '1st tweet' --post_id 1

$ python3 ./main.py tweet --app_id 156806034 --txt 'Hello world. This is the 1st AlgoBlog tweet.' --post_id 1
posting tweet: 1
Resulting id tweet:  id:1
Next you should: get_tweet --app_id 156806034 --post_id 1

$ python3 ./main.py get_tweet --app_id 156806034 --post_id 1
tweet:  Hello world. This is the 1st AlgoBlog tweet.
tweet tstamp:  1675437480

python3 ./main.py tweet --app_id 156806034 --txt 'I hope that even my worst critics remain on Twitter, because that is what free speech means' --post_id 2
posting tweet: 2
Resulting id tweet:  id:2

$ python3 twtxtwebserver.py
192.168.1.123 - - [01/Feb/2023 22:58:02] "GET /twtxt.txt HTTP/1.1" 200 -
```

# registry
```
$ python3 ./main.py deploy_registry
Deployed app in txid RMLLDVVGN7SE332JLWH7HZ6B6WINXWHTJ6C2SGNS5KEBO34RHKMA
            App ID: 1810
            Address: N2CHKSKYDSP55QMEXNHWI4ZFLGK5BTIXPKV6LABYHPML4HJHRESI2U4IPE

bootstrap result:  booted
- app_id:  1810

$ python3 ./main.py register --nick tomo2 --username tomo --blog_app_id 1800 --app_id 1810
register result:  tomo

```

# twtxt
```
$ twtxt following
➤ twtxt @ https://buckket.org/twtxt_news.txt
➤ algotomo @ http://192.168.1.100:4443/twtxt.txt

$ twtxt timeline
➤ twtxt (7 years ago)
Fiat Lux!
➤ twtxt (7 years ago)
twtxt 1.1.0 just got released: https://github.com/buckket/twtxt/releases/tag/v1.1.0 - Upgrade via: pip3 install --upgrade twtxt
➤ twtxt (7 years ago)
twtxt 1.2.0 just got released: https://github.com/buckket/twtxt/releases/tag/v1.2.0 - Upgrade via: pip3 install --upgrade twtxt
➤ twtxt (7 years ago)
twtxt 1.2.1 just got released: https://github.com/buckket/twtxt/releases/tag/v1.2.1 - Upgrade via: pip3 install --upgrade twtxt
➤ twtxt (7 years ago)
This update adds an option to include user’s nick and url in twtxt’s user-agent string for greater discovery! Check the docs.
➤ twtxt (6 years ago)
Apparently a few new people discovered twtxt, have fun poking around :)
➤ algotomo (a day ago)
Hello world. This is the 1st AlgoBlog tweet.
➤ algotomo (a day ago)
I hope that even my worst critics remain on Twitter, because that is what free speech means
➤ tomotxt (4 minutes ago)
I don't have anything clever to say

```
