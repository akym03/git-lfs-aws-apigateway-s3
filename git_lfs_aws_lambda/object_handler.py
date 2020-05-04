from logging import getLogger

from git_lfs_aws_lambda.action import Action
from git_lfs_aws_lambda.handler import Handler
from git_lfs_aws_lambda.lfs_error import LfsError


class ObjectHandler(Handler):
    TRANSFER_TYPE = "basic"
    LINK_EXPIRATION_TIME = 900

    logger = getLogger(__name__)

    def __init__(self, operation, datastore, endpoint, resource_path):

        self.datastore = datastore
        self.endpoint = endpoint
        self.resource_path = resource_path

        if(operation == "upload"):
            self.process = self.__upload_process
        elif(operation == "download"):
            self.process = self.__download_process
        elif(operation == "verify"):
            self.process = self.__verify_process
        else:
            raise LfsError(401, f"Unsupported object operation: [{operation}]")

    def __get_verify_url(self):
        endpoint = self.endpoint
        resource = self.resource_path
        return f"http://{endpoint}{resource}/verify"

    def __verify_transfer_type(self, request):
        if ("transfers" in request and (ObjectHandler.TRANSFER_TYPE not in request["transfers"])):
            transfer = request["transfers"]
            raise LfsError(422, f"Unsupported transfer type: {transfer}")

    def __get_veirfy_action(self, key):
        json = Action(self.__get_verify_url()).to_dict()
        return json

    def __get_upload_action(self, key):
        json = Action(self.datastore.get_upload_url(key), ObjectHandler.LINK_EXPIRATION_TIME).to_dict()
        return json

    def __get_download_action(self, key):
        json = Action(self.datastore.get_download_url(key), ObjectHandler.LINK_EXPIRATION_TIME).to_dict()
        return json

    def __handle_upload(self, request):
        response = []
        for request_object in request["objects"]:
            directive = ObjectHandler.blank_directive_for(request_object)
            try:
                if (self.datastore.exists(directive["oid"])):
                    # If we already have this object, no action is necessary.
                    continue

                directive["actions"] = {
                    "upload": self.__get_upload_action(directive["oid"]),
                    "verify": self.__get_veirfy_action(directive["oid"])
                }

            except LfsError as e:
                directive["error"] = {
                    "code": e.args[0],
                    "message": e.args[1]
                }
            except Exception as e:
                ObjectHandler.logger.exception(e)
                directive["error"] = {
                    "code": 500,
                    "message": e.args[0]
                }
            finally:
                response.append(directive)

        return response

    def __handle_download(self, request):
        response = []
        for request_object in request["objects"]:
            directive = ObjectHandler.blank_directive_for(request_object)
            try:
                if (not self.datastore.exists(directive["oid"])):
                    oid = directive["oid"]
                    directive["error"] = {
                        "code": 404,
                        "message": f"Object {oid} not exist."
                    }
                    continue

                directive["actions"] = {
                    "download": self.__get_download_action(directive["oid"]),
                }

            except LfsError as e:
                directive["error"] = {
                    "code": e.args[0],
                    "message": e.args[1]
                }
            except Exception as e:
                ObjectHandler.logger.exception(e)
                directive["error"] = {
                    "code": 500,
                    "message": e.args[0]
                }
            finally:
                response.append(directive)

        return response

    def __handle_verify(self, request):
        oid = request["oid"]
        info = self.datastore.get_info(oid)

        result = "NotFound" if info is None else "Verified" if info["ContentLength"] == request["size"] else "WrongSize"
        found = None if info is None else {"oid": request["oid"], "size": info["ContentLength"]}

        return {
            "result": result,
            "request": request,
            "found": found
        }

    def __to_response_format(self, response):
        return {
            "transfer": ObjectHandler.TRANSFER_TYPE,
            "objects": response
        }

    def __to_response_format_of_verify(self, request, response):
        result = response["result"]
        if (result == "Verified"):
            return request
        if (result == "NotFound"):
            oid = request["oid"]
            raise LfsError(404, f"Object {oid} not found.")
        elif (result == "WrongSize"):
            request_size = request["size"]
            found_size = response["found"]["size"]
            raise LfsError(411, f"Expected object of size {request_size} but found {found_size}")

        raise Exception(f"Unkown verification result {result}")

    def __upload_process(self, request):
        self.__verify_transfer_type(request)
        response = self.__handle_upload(request)
        return self.__to_response_format(response)

    def __download_process(self, request):
        self.__verify_transfer_type(request)
        response = self.__handle_download(request)
        return self.__to_response_format(response)

    def __verify_process(self, request):
        verified = self.__handle_verify(request)
        return self.__to_response_format_of_verify(request, verified)

    def get_doc_url(self, status_code):
        return "https://github.com/git-lfs/git-lfs/blob/master/docs/api/batch.md"

    @classmethod
    def blank_directive_for(self, item):
        return {
            "oid": item["oid"],
            "size": item["size"],
            "authenticated": True
        }
