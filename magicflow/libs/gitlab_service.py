import base64
import os
import re
import sys
import time
import yaml
from base64 import b64decode
import gitlab
from typing import TypedDict
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger(__name__)

'''
GitlabDriver is a driver for Gitlab API.
'''


class GitlabDriver():

    def __init__(self, authkey, project):

        # Parse command line arguments
        self.url = "https://gitlab.com"
        self.authkey = authkey
        self.project_name = project
        self.project = None
        self.mrs = None  # list of all merge requests
        # Create python-magicflow server instance
        #        try:
        self.server = gitlab.Gitlab(self.url,
                                    self.authkey,
                                    api_version=4,
                                    ssl_verify=True)
        # Get an instance of the project and store it off
        self.project = self.server.projects.get(self.project_name)

    def list_mrs(self, appid):
        self.appid = appid
        # Get all MRs in the project and print some info about them
        mrs = self.project.mergerequests.list(all=20,
                                              state='merged',
                                              order_by='updated_at')
        mr_list = []
        for mr in mrs:
            logger.debug('One MR =%s' % mr)
            mr_id = mr.iid
            mr_projectid = mr.project_id
            mr_title = re.escape(mr.title)
            mr_state = mr.state
            if mr.merged_by is None:
                merged_by = mr.author['username']
                merged_at = mr.updated_at
            else:
                merged_by = mr.merged_by['username']
                merged_at = mr.merged_at
            mr_url = mr.web_url
            source_branch = mr.source_branch
            one_mr = {
                "id": "" + self.appid + str(mr_id) + "",
                "attributes": {
                    "source": "magicflow-hook",
                    "type": "magicflow-mr",
                    "date": merged_at,
                    "author": merged_by
                },
                "message": mr_title,
                "data": {
                    "mrid": mr_id,
                    "projectid": mr_projectid,
                    "title": mr_title,
                    "state": mr_state,
                    "merged_by": merged_by,
                    "merged_at": merged_at,
                    "url": mr_url,
                    "source_branch": source_branch
                }
            }
            mr_list.append(one_mr)
        return mr_list

    def get_pro_file(self, file_name, _branch):
        self.file_name = file_name
        self.branch = _branch
        with open('stage.yaml', 'wb') as f:
            self.project.files.raw(file_path=self.file_name,
                                   ref=self.branch,
                                   streamed=True,
                                   action=f.write)

    def upload_file(self, local_file, remote_file):
        try:
            file = self.project.files.get(file_path=remote_file, ref="master")
            file.content = base64.b64encode(open(local_file,
                                                 'rb').read()).decode()
            file.save(branch='master',
                      commit_message='Update ACL audit file',
                      encoding='base64')
            return 1
        except gitlab.exceptions.GitlabCreateError:
            logger.error('Audit file exist')
        except:
            with open(local_file, 'r') as acl_export:
                file_content = acl_export.read()
            self.project.files.create({
                'file_path': remote_file,
                'branch': "master",
                'content': file_content,
                'author_email': "kafkagit@project_34437336_bot1",
                'author_name': "kafka_audit",
                'commit_message': 'Audit ACL created'
            })

    def check_approval(self, mr_iid):
        """
        Checks merge request for approval.
        Parameters:
          mr_iid - project MR ID(short ID, found in URL) ex. 243
        """
        logger.info(f'Checking merge request ID: {mr_iid} approval status.')
        try:
            mr = self.project.mergerequests.get(mr_iid)
            _mr = {"id": mr.iid, "state": mr.state}
        except gitlab.exceptions.GitlabGetError as exc:
            logger.info(
                f'Merge request ID: {mr_iid} was not found. Error message {exc}'
            )
            return False
        mr_approval_state = "False"
        rules = mr.approval_state.get().attributes['rules']
        logger.debug(f' MR rules: {rules}')
        for rule in rules:
            if rule['rule_type'] in ['regular', 'any_approver']:
                if rule['approved']:
                    mr_approval_state = rule['approved']
                else:
                    return {"mr": _mr, "approval": "False"}
            else:
                pass

        approvers_list = []
        for rule in rules:
            logger.debug(rule)

            if rule['rule_type'] == 'regular':
                for rule_approver in rule['approved_by']:
                    approvers_list.append(rule_approver['name'])

        logger.info(
            f"Merge request ID: {mr_iid} approved by {', '.join(approvers_list)}!"
        )

        return {
            "approval": str(mr_approval_state),
            "approvers": approvers_list,
            "mr": _mr
        }

    def check_mr_pipeline_status(self, mr_iid):
        try:
            mr = self.project.mergerequests.get(mr_iid)
        except gitlab.exceptions.GitlabGetError as exc:
            logger.info(
                f'Merge request ID: {mr_iid} was not found. Error message {exc}'
            )
            return False

        mr_pipelines = mr.pipelines.list()

        pipelines = []
        for pipeline in mr_pipelines:
            pipelines.append({
                "status": pipeline.status,
                "url": pipeline.web_url,
                "id": pipeline.id
            })

        return pipelines

    def check_pipeline_job_status(self, pipeline_job_id):
        try:
            _job = self.project.jobs.get(pipeline_job_id)
        except gitlab.exceptions.GitlabGetError as exc:
            logger.info(
                f'Merge request ID: {pipeline_job_id} was not found. Error message {exc}'
            )
            return False

        _jobs = []
        _jobs.append({
            "status": _job.status,
            "url": _job.web_url,
            "id": _job.id
        })

        return _jobs

    def play_pipeline_job(self, pipeline_id):
        try:
            p = self.project.pipelines.get(pipeline_id)
        except gitlab.exceptions.GitlabGetError as exc:
            logger.info(
                f'Pipeline ID: {pipeline_id} was not found. Error message {exc}'
            )
            return {"pipeline_id": str(pipeline_id)}
        # 1st manual job
        pipeline_job_id = p.jobs.list()[0].id
        logger.info(pipeline_job_id)
        web_url = p.jobs.list()[0].web_url

        job = self.project.jobs.get(pipeline_job_id, lazy=True)
        play = job.play()
        return {
            "pipeline_job_id": str(pipeline_job_id),
            "pipeline_id": pipeline_id,
            "web_url": web_url
        }

    def merge(self, mr_iid):
        """
        Merges a merge request
        Parameters:
          mr_iid - project MR ID(short ID, found in URL) ex. 243
        """
        logger.info(f'Merging merge request {mr_iid}.')
        try:
            mr = self.project.mergerequests.get(mr_iid)
        except gitlab.exceptions.GitlabGetError as exc:
            logger.info(
                f'Merge request {mr_iid} was not found. Error message {exc}')
            return {"mr_id": str(mr_iid), "result": f"Failed due to {exc}"}

        mr_merge_state = mr.state
        mr_title = mr.title

        if mr_merge_state == 'closed':
            logger.info(
                f'Merge request ID: {mr_iid}, Title: {mr_title}, closed.')
            return {
                "mr_id": str(mr_iid),
                "result": f'MR {mr_title} id closed.'
            }
        elif mr_merge_state == 'merged':
            mr_merge_user = mr.merge_user['name']
            logger.info(f'Merge request ID: {mr_iid}, Title: {mr_title}, '
                        f'already merged by {mr_merge_user}.')
            return {
                "mr_id": str(mr_iid),
                "result": f'MR {mr_title} already merged by {mr_merge_user}.'
            }

        if mr.merge_status == 'cannot_be_merged':
            logger.info(
                f'Merge request {mr_iid} cannot be merged. Merge conflicts! '
                f'Please check {mr.web_url}')
            return {
                "mr_id":
                str(mr_iid),
                "result":
                f'MR {mr_iid} cannot be merged. Merge conflicts! '
                f'Please check {mr.web_url}'
            }

        mr.merge()

        mr_merge_user = mr.merge_user['name']
        mr_merge_state = mr.state

        if mr_merge_state == 'merged':
            logger.info(
                f'Merge request ID: {mr_iid}, Title: {mr_title}, merged by {mr_merge_user}!'
            )
            return {"mr_id": str(mr_iid), "result": f'MR merged!'}

        return {"mr_id": str(mr_iid), "result": "Failed"}

    def validate_merge_request(self, job_id):
        """
        Validate if Merge Requests already exists. Each Merge
        Request which was created by Data Platform Self Service
        should start with a self service job ID:
          - "123 Create MySQL 8 in monolith capability"

        Returns:
            Function returns True if there is already existing
            Merge Request opened with the self service job ID prefix.
        """

        mrs = self.project.mergerequests.list(state='opened')
        for mr in mrs:
            if mr.title.split(" ")[0] == job_id:
                logger.info(f'Duplicate MR found with a job ID {job_id}')
                return False
            return True

    def get_project_file(self, path, branch='master'):
        """
        Get single project file from Gitlab project.

        Returns:
            Function returns Gitlab file object.
        """
        try:
            f = self.project.files.get(file_path=path, ref=branch)
            # f["exists"] = True
            return f
        except:
            return False

    def push_mr(self,
                *args,
                branch="job_id",
                title="selfservice update",
                description="TBU",
                jira_ticket="DP-XXX"):
        """
        Create a branch and push Merge request.

        Inputs:
            Gitlab projectfile(s) and Job ID.

        Returns:
            Function returns Gitlab Merge request URL.
        """
        if any(arg for arg in args):
            branch_name = branch
            logger.info("Branch to be created is %s" % branch_name)
            try:
                branch = self.project.branches.create({
                    "branch": branch_name,
                    "ref": "master"
                })
            except gitlab.exceptions.GitlabCreateError:
                logger.error(
                    "Branch %s creation failure, branch may exist already" %
                    branch_name)
                logger.info(self.project.branches.list(all=True))
                if branch_name in str(self.project.branches.list(all=True)):
                    logger.info("Branch %s exists already" % branch_name)
                    mrs = self.project.mergerequests.list(
                        all=20, state='opened', order_by='updated_at')
                    for mr in mrs:
                        if branch_name == mr.source_branch:
                            logger.info(
                                "MR created already from source branch %s, no MR needed"
                                % branch_name)
                            return {
                                "mr_id": str(mr.iid),
                                "mr_url": mr.web_url,
                                "parameters": {
                                    "mr_created": "False"
                                }
                            }
            for arg in args:
                if arg:
                    logger.debug("Arg type is %s" % type(arg))
                    if type(arg) is dict:
                        self.project.files.create({
                            'file_path':
                            arg["file_path"],
                            'branch':
                            branch.name,
                            'content':
                            arg["content"],
                            'author_email':
                            "MagicFlow worker",
                            'author_name':
                            "MagicFlow worker",
                            'commit_message':
                            f'{jira_ticket} Automated provisioning values update'
                        })
                    else:
                        arg.save(
                            branch=branch.name,
                            commit_message=
                            f'{jira_ticket} Automated provisioning values update'
                        )
            mr = self.project.mergerequests.create({
                "source_branch": branch.name,
                "target_branch": "master",
                "title": title,
                "description": description,
                'labels': [branch.name]
            })
            logger.info("MR created, please ask for review and approval")
            return {
                "mr_id": str(mr.iid),
                "mr_url": mr.web_url,
                "parameters": {
                    "mr_created": "True"
                }
            }
