from neo.Core.Blockchain import Blockchain
from neo.Core.TX.Transaction import TransactionOutput, ContractTransaction
from neo.Core.TX.TransactionAttribute import TransactionAttribute, TransactionAttributeUsage
from neo.SmartContract.ContractParameterContext import ContractParametersContext
from neo.Network.NodeLeader import NodeLeader
from neo.Prompt.Utils import get_arg, get_from_addr, get_asset_id, lookup_addr_str, get_tx_attr_from_args, \
    get_owners_from_params, get_fee, get_change_addr, get_asset_amount
from neo.Prompt.Commands.Tokens import do_token_transfer, amount_from_string
from neo.Prompt.Commands.Invoke import gather_signatures
from neo.Wallets.NEP5Token import NEP5Token
from neocore.UInt256 import UInt256
from neocore.Fixed8 import Fixed8
import json
from prompt_toolkit import prompt
import traceback
from neo.Prompt.PromptData import PromptData
from neo.Prompt.CommandBase import CommandBase, CommandDesc, ParameterDesc
from logzero import logger


class CommandWalletSend(CommandBase):

    def __init__(self):
        super().__init__()

    def execute(self, arguments):
        framework = construct_send_basic(PromptData.Wallet, arguments)
        if type(framework) is list:
            return process_transaction(PromptData.Wallet, contract_tx=framework[0], scripthash_from=framework[1],
                                       fee=framework[2], owners=framework[3], user_tx_attributes=framework[4])
        return framework

    def command_desc(self):
        p1 = ParameterDesc('assetId or name', 'the asset you wish to send')
        p2 = ParameterDesc('address', 'the NEO address you will send to')
        p3 = ParameterDesc('amount', 'the amount of the asset you wish to send')
        p4 = ParameterDesc('--from-addr={addr}', 'specify the NEO address you wish to send from', optional=True)
        p5 = ParameterDesc('--fee={priority_fee}', 'attach a fee to give your tx priority (> 0.001)', optional=True)
        p6 = ParameterDesc('--owners=[{addr}, ...]', 'specify tx owners', optional=True)
        p7 = ParameterDesc('--tx-attr=[{"usage": <value>,"data":"<remark>"}, ...]', 'specify unique tx attributes', optional=True)
        params = [p1, p2, p3, p4, p5, p6, p7]
        return CommandDesc('send', 'send an asset', params=params)


class CommandWalletSendMany(CommandBase):

    def __init__(self):
        super().__init__()

    def execute(self, arguments):
        framework = construct_send_many(PromptData.Wallet, arguments)
        if type(framework) is list:
            return process_transaction(PromptData.Wallet, contract_tx=framework[0], scripthash_from=framework[1], scripthash_change=framework[2],
                                       fee=framework[3], owners=framework[4], user_tx_attributes=framework[5])
        return framework

    def command_desc(self):
        p1 = ParameterDesc('number of outgoing tx', 'the number of tx you wish to send')
        p2 = ParameterDesc('--change-addr={addr}', 'specify the change address', optional=True)
        p3 = ParameterDesc('--from-addr={addr}', 'specify the NEO address you wish to send from', optional=True)
        p4 = ParameterDesc('--fee={priority_fee}', 'attach a fee to give your tx priority (> 0.001)', optional=True)
        p5 = ParameterDesc('--owners=[{addr}, ...]', 'specify tx owners', optional=True)
        p6 = ParameterDesc('--tx-attr=[{"usage": <value>,"data":"<remark>"}, ...]', 'specify unique tx attributes', optional=True)
        params = [p1, p2, p3, p4, p5, p6]
        return CommandDesc('sendmany', 'send multiple contract transactions', params=params)


class CommandWalletSign(CommandBase):

    def __init__(self):
        super().__init__()

    def execute(self, arguments):
        jsn = get_arg(arguments)
        return parse_and_sign(PromptData.Wallet, jsn)

    def command_desc(self):
        p1 = ParameterDesc('jsn', 'transaction in JSON format')
        params = [p1]
        return CommandDesc('sign', 'sign multi-sig tx', params=params)


def construct_send_basic(wallet, arguments):
    if len(arguments) < 3:
        print("Not enough arguments")
        return

    arguments, from_address = get_from_addr(arguments)
    arguments, priority_fee = get_fee(arguments)
    arguments, user_tx_attributes = get_tx_attr_from_args(arguments)
    arguments, owners = get_owners_from_params(arguments)
    to_send = get_arg(arguments)
    address_to = get_arg(arguments, 1)
    amount = get_arg(arguments, 2)

    assetId = get_asset_id(wallet, to_send)
    if assetId is None:
        print("Asset id not found")
        return

    scripthash_to = lookup_addr_str(wallet, address_to)
    if scripthash_to is None:
        logger.debug("invalid address")
        return

    scripthash_from = None
    if from_address is not None:
        scripthash_from = lookup_addr_str(wallet, from_address)
        if scripthash_from is None:
            logger.debug("invalid address")
            return

    # if this is a token, we will use a different
    # transfer mechanism
    if type(assetId) is NEP5Token:
        return do_token_transfer(assetId, wallet, from_address, address_to, amount_from_string(assetId, amount),
                                 tx_attributes=user_tx_attributes)

    f8amount = get_asset_amount(amount, assetId)
    if f8amount is False:
        logger.debug("invalid amount")
        return
    if float(amount) == 0:
        print("amount cannot be 0")
        return

    fee = Fixed8.Zero()
    if priority_fee is not None:
        fee = priority_fee
        if fee is False:
            logger.debug("invalid fee")
            return

    output = TransactionOutput(AssetId=assetId, Value=f8amount, script_hash=scripthash_to)
    contract_tx = ContractTransaction(outputs=[output])
    return [contract_tx, scripthash_from, fee, owners, user_tx_attributes]


def construct_send_many(wallet, arguments):
    if len(arguments) is 0:
        print("Not enough arguments")
        return

    outgoing = get_arg(arguments, convert_to_int=True)
    if outgoing is None:
        print("invalid outgoing number")
        return
    if outgoing < 1:
        print("outgoing number must be >= 1")
        return

    arguments, from_address = get_from_addr(arguments)
    arguments, change_address = get_change_addr(arguments)
    arguments, priority_fee = get_fee(arguments)
    arguments, owners = get_owners_from_params(arguments)
    arguments, user_tx_attributes = get_tx_attr_from_args(arguments)

    output = []
    for i in range(outgoing):
        print('Outgoing Number ', i + 1)
        to_send = prompt("Asset to send: ")
        assetId = get_asset_id(wallet, to_send)
        if assetId is None:
            print("Asset id not found")
            return
        if type(assetId) is NEP5Token:
            print('Sendmany does not support NEP5 tokens')
            return
        address_to = prompt("Address to: ")
        scripthash_to = lookup_addr_str(wallet, address_to)
        if scripthash_to is None:
            logger.debug("invalid address")
            return
        amount = prompt("Amount to send: ")
        f8amount = get_asset_amount(amount, assetId)
        if f8amount is False:
            logger.debug("invalid amount")
            return
        if float(amount) == 0:
            print("amount cannot be 0")
            return
        tx_output = TransactionOutput(AssetId=assetId, Value=f8amount, script_hash=scripthash_to)
        output.append(tx_output)
    contract_tx = ContractTransaction(outputs=output)

    scripthash_from = None

    if from_address is not None:
        scripthash_from = lookup_addr_str(wallet, from_address)
        if scripthash_from is None:
            logger.debug("invalid address")
            return

    scripthash_change = None

    if change_address is not None:
        scripthash_change = lookup_addr_str(wallet, change_address)
        if scripthash_change is None:
            logger.debug("invalid address")
            return

    fee = Fixed8.Zero()
    if priority_fee is not None:
        fee = priority_fee
        if fee is False:
            logger.debug("invalid fee")
            return

    print("sending with fee: %s " % fee.ToString())
    return [contract_tx, scripthash_from, scripthash_change, fee, owners, user_tx_attributes]


def process_transaction(wallet, contract_tx, scripthash_from=None, scripthash_change=None, fee=None, owners=None, user_tx_attributes=None):
    try:
        tx = wallet.MakeTransaction(tx=contract_tx,
                                    change_address=scripthash_change,
                                    fee=fee,
                                    from_addr=scripthash_from)

        if tx is None:
            logger.debug("insufficient funds")
            return

        # password prompt
        passwd = prompt("[Password]> ", is_password=True)
        if not wallet.ValidatePassword(passwd):
            print("incorrect password")
            return

        standard_contract = wallet.GetStandardAddress()

        if scripthash_from is not None:
            signer_contract = wallet.GetContract(scripthash_from)
        else:
            signer_contract = wallet.GetContract(standard_contract)

        if not signer_contract.IsMultiSigContract and owners is None:
            data = standard_contract.Data
            tx.Attributes = [TransactionAttribute(usage=TransactionAttributeUsage.Script,
                                                  data=data)]

        # insert any additional user specified tx attributes
        tx.Attributes = tx.Attributes + user_tx_attributes

        if owners:
            owners = list(owners)
            for owner in owners:
                tx.Attributes.append(
                    TransactionAttribute(usage=TransactionAttributeUsage.Script, data=owner))

        context = ContractParametersContext(tx, isMultiSig=signer_contract.IsMultiSigContract)
        wallet.Sign(context)

        if owners:
            owners = list(owners)
            gather_signatures(context, tx, owners)

        if context.Completed:

            tx.scripts = context.GetScripts()

            #            print("will send tx: %s " % json.dumps(tx.ToJson(),indent=4))

            relayed = NodeLeader.Instance().Relay(tx)

            if relayed:
                wallet.SaveTransaction(tx)

                print("Relayed Tx: %s " % tx.Hash.ToString())
                return tx
            else:

                print("Could not relay tx %s " % tx.Hash.ToString())

        else:
            print("Transaction initiated, but the signature is incomplete")
            print(json.dumps(context.ToJson(), separators=(',', ':')))
            return

    except Exception as e:
        print("could not send: %s " % e)
        traceback.print_stack()
        traceback.print_exc()

    return


def parse_and_sign(wallet, jsn):
    try:
        context = ContractParametersContext.FromJson(jsn)
        if context is None:
            print("Failed to parse JSON")
            return

        wallet.Sign(context)

        if context.Completed:

            print("Signature complete, relaying...")

            tx = context.Verifiable
            tx.scripts = context.GetScripts()

            wallet.SaveTransaction(tx)

            print("will send tx: %s " % json.dumps(tx.ToJson(), indent=4))

            relayed = NodeLeader.Instance().Relay(tx)

            if relayed:
                print("Relayed Tx: %s " % tx.Hash.ToString())
            else:
                print("Could not relay tx %s " % tx.Hash.ToString())
            return
        else:
            print("Transaction initiated, but the signature is incomplete")
            print(json.dumps(context.ToJson(), separators=(',', ':')))
            return

    except Exception as e:
        print("could not send: %s " % e)
        traceback.print_stack()
        traceback.print_exc()
