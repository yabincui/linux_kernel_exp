#!/usr/bin/python

import logging
import os
import re
import subprocess
import sys


"""
Generate policy.conf based on contents:
    security_classes
    initial_sids
    access_vecors
    te_macros
    *.te
    roles_decl
    roles
    users
    init_sid_contexts
    fs_use
    genfs_contexts

"""

def get_file_in_script_dir(filename):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)

def read_file(filepath):
    with open(filepath, "r") as fh:
       return fh.read()

def log_debug(msg):
    logging.debug(msg)

def log_fatal(msg):
    raise Exception(msg)
logging.getLogger().setLevel(logging.DEBUG)

def run_cmd(args, input="", check=True, shell=False):
    subproc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=shell)
    (stdoutdata, _) = subproc.communicate(input)
    returncode = subproc.returncode
    log_debug("cmd: %s" % args)
    log_debug("%s" % stdoutdata)
    log_debug("run cmd: %s [result %s]" % (args, returncode))
    if check and returncode != 0:
        log_fatal("cmd failed")
    return stdoutdata

def call_cmd(args):
    log_debug("cmd: %s" % args)
    subprocess.check_call(args)

def run_script(content):
    with open("_temp_script.sh", "w") as fh:
        fh.write("set -ex\n")
        fh.write(content)
    call_cmd(["sh", "_temp_script.sh"])

class SecurityClassMapping(object):
    def __init__(self, name = "", perms = []):
        self.name = name
        self.perms = perms[:]

    def __str__(self):
        return "Mapping(%s, %s)" % (self.name, self.perms)

    def __repr__(self):
        return self.__str__()

class SecurityClassMappingGenerator(object):
    TOKEN_DEFINE = 0
    TOKEN_VARIABLE = 1
    TOKEN_STRING = 2
    TOKEN_LBRACE = 3
    TOKEN_RBRACE = 4
    TOKEN_NEWLINE = 6
    TOKEN_EOF = 7

    def __init__(self, input_filename):
        self.input_filename = input_filename
        with open(self.input_filename, 'r') as fh:
            self.data = fh.read()
        self.data_i = 0
        self.defines = {}
        self.mappings = []
        self.token_value = None
        self._parse()

    def _parse(self):
        while True:
            token = self._getToken()
            if token == self.TOKEN_EOF:
                break
            if token == self.TOKEN_DEFINE:
                token = self._getToken()
                assert token == self.TOKEN_VARIABLE
                varname = self.token_value
                values = []
                while True:
                    token = self._getToken()
                    if token == self.TOKEN_STRING:
                        values.append(self.token_value)
                    elif token == self.TOKEN_VARIABLE and self.token_value in self.defines:
                        values += self.defines[self.token_value]
                    else:
                        break
                self.defines[varname] = values
            elif token == self.TOKEN_VARIABLE and self.token_value == "struct":
                token = self._getToken()
                if token != self.TOKEN_VARIABLE or self.token_value != "security_class_mapping":
                    continue
                token = self._getToken()
                if token != self.TOKEN_VARIABLE or self.token_value != "secclass_map":
                    continue
                while self._getToken() != self.TOKEN_LBRACE:
                    continue
                lparen_level = 1
                while lparen_level > 0:
                    token = self._getToken()
                    if token == self.TOKEN_LBRACE:
                        lparen_level += 1
                    elif token == self.TOKEN_RBRACE:
                        lparen_level -= 1
                    elif token == self.TOKEN_STRING:
                        if lparen_level == 2:
                            self.mappings.append(SecurityClassMapping(self.token_value))
                        elif lparen_level == 3:
                            self.mappings[-1].perms.append(self.token_value)
                    elif token == self.TOKEN_VARIABLE:
                        if lparen_level == 3 and self.token_value in self.defines:
                            self.mappings[-1].perms += self.defines[self.token_value]


    def _getToken(self):
        s = self.data
        n = len(s)
        i = self.data_i
        token = -1

        while token == -1 and i < n:
            if s[i] == '#':
                j = i + 1
                while j < n and self.isalnum(s[j]):
                    j += 1
                if s[i:j] == '#define':
                    token = self.TOKEN_DEFINE
                i = j
            elif s[i] == '{':
                token = self.TOKEN_LBRACE
                i += 1
            elif s[i] == '}':
                token = self.TOKEN_RBRACE
                i += 1
            elif s[i] == '\n':
                token = self.TOKEN_NEWLINE
                i += 1
            elif s[i] == '\"':
                j = i + 1
                while j < n and s[j] != '\"':
                    j += 1
                token = self.TOKEN_STRING
                self.token_value = s[i+1:j]
                i = j + 1
            elif self.isalnum(s[i]):
                j = i + 1
                while j < n and self.isalnum(s[j]):
                    j += 1
                token = self.TOKEN_VARIABLE
                self.token_value = s[i:j]
                i = j
            elif s[i] == '\\':
                if i + 1 < n and s[i + 1] == '\n':
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        if token == -1:
            token = self.TOKEN_EOF
        self.data_i = i
        return token


    def isalnum(self, c):
        return (c >= '0' and c <= '9') or (c >= 'a' and c <= 'z') or \
            (c >= 'A' and c <= 'Z') or c == '_'


    def genMappings(self):
        return self.mappings


class SidGenerator(object):
    TOKEN_DEFINE = 0
    TOKEN_VARIABLE = 1
    TOKEN_STRING = 2
    TOKEN_LBRACE = 3
    TOKEN_RBRACE = 4
    TOKEN_NEWLINE = 6
    TOKEN_EOF = 7

    def __init__(self, input_filename):
        self.input_filename = input_filename
        with open(self.input_filename, 'r') as fh:
            self.data = fh.read()
        self.data_i = 0
        self.sid_list = []
        self.token_value = None
        self._parse()

    def _parse(self):
        while True:
            token = self._getToken()
            if token == self.TOKEN_EOF:
                break
            elif token == self.TOKEN_VARIABLE and self.token_value == "initial_sid_to_string":
                while self._getToken() != self.TOKEN_LBRACE:
                    continue
                lparen_level = 1
                while lparen_level > 0:
                    token = self._getToken()
                    if token == self.TOKEN_LBRACE:
                        lparen_level += 1
                    elif token == self.TOKEN_RBRACE:
                        lparen_level -= 1
                    elif token == self.TOKEN_STRING:
                        if lparen_level == 1:
                            self.sid_list.append(self.token_value)

    def _getToken(self):
        s = self.data
        n = len(s)
        i = self.data_i
        token = -1

        while token == -1 and i < n:
            if s[i] == '#':
                j = i + 1
                while j < n and self.isalnum(s[j]):
                    j += 1
                if s[i:j] == '#define':
                    token = self.TOKEN_DEFINE
                i = j
            elif s[i] == '{':
                token = self.TOKEN_LBRACE
                i += 1
            elif s[i] == '}':
                token = self.TOKEN_RBRACE
                i += 1
            elif s[i] == '\n':
                token = self.TOKEN_NEWLINE
                i += 1
            elif s[i] == '\"':
                j = i + 1
                while j < n and s[j] != '\"':
                    j += 1
                token = self.TOKEN_STRING
                self.token_value = s[i+1:j]
                i = j + 1
            elif self.isalnum(s[i]):
                j = i + 1
                while j < n and self.isalnum(s[j]):
                    j += 1
                token = self.TOKEN_VARIABLE
                self.token_value = s[i:j]
                i = j
            elif s[i] == '\\':
                if i + 1 < n and s[i + 1] == '\n':
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        if token == -1:
            token = self.TOKEN_EOF
        self.data_i = i
        return token

    def isalnum(self, c):
        return (c >= '0' and c <= '9') or (c >= 'a' and c <= 'z') or \
            (c >= 'A' and c <= 'Z') or c == '_'

    def genSidList(self):
        return self.sid_list


class PolicyGenerator(object):
    def __init__(self, output_filename):
        self.output_filename = output_filename
        self.out_fh = open(output_filename, 'w')
        classmap_header_file = get_file_in_script_dir("classmap.h")
        mapping_generator = SecurityClassMappingGenerator(classmap_header_file)
        self.security_class_mappings = mapping_generator.genMappings()
        #print "security class mappings: %s" % self.security_class_mappings
        sid_to_string_header_file = get_file_in_script_dir("initial_sid_to_string.h")
        sid_generator = SidGenerator(sid_to_string_header_file)
        self.sid_list = sid_generator.genSidList()

    def close(self):
        self.out_fh.close()

    def _write(self, content = ""):
        self.out_fh.write(content + '\n')

    def genSecurityClasses(self):
        for mapping in self.security_class_mappings:
            self._write("class %s" % mapping.name)
        self._write()

    def genInitialSids(self):
        for sid in self.sid_list:
            self._write("sid %s" % sid)
        self._write()

    def genAccessVectors(self):
        for mapping in self.security_class_mappings:
            self._write("class %s" % mapping.name)
            self._write("{")
            for perm in mapping.perms:
                self._write("\t%s" % perm)
            self._write("}\n")
        self._write()

    def genTeMacros(self):
        data = read_file(get_file_in_script_dir("te_macros"))
        self._write("# te_macros")
        self._write(data)

    def _genBaseType(self):
        for mapping in self.security_class_mappings:
            self._write("allow base_t base_t:%s *;" % mapping.name)

    def genTes(self):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        files = os.listdir(dirpath)
        for file in files:
            if file.endswith(".te"):
                data = read_file(os.path.join(dirpath, file))
                self._write("# %s" % file)
                self._write(data)
        self._genBaseType()

    def genRolesDecl(self):
        self._write("role base_r;")

    def genRoles(self):
        self._write("role base_r types { domain file_type };")

    def genUsers(self):
        self._write("user user_u roles { base_r };")

    def genInitialSidContexts(self):
        for sid in self.sid_list:
            self._write("sid %s user_u:base_r:base_t" % sid)
        self._write()

    def genFsUse(self):
        self._write("fs_use_xattr ext4 user_u:base_r:base_t;")
        for fs in ["eventpollfs", "pipefs", "sockfs"]:
            self._write("fs_use_task %s user_u:base_r:base_t;" % fs)

    def genGenfsContexts(self):
        self._write("genfscon proc / user_u:base_r:base_t")



def generate_policy(output_filename):
    generator = PolicyGenerator(output_filename)
    generator.genSecurityClasses()
    generator.genInitialSids()
    generator.genAccessVectors()
    generator.genTeMacros()
    generator.genTes()
    generator.genRolesDecl()
    generator.genRoles()
    generator.genUsers()
    generator.genInitialSidContexts()
    generator.genFsUse()
    generator.genGenfsContexts()
    generator.close()

def main():
    generate_policy('policy.conf.before_m4')
    run_script("m4 policy.conf.before_m4 >policy.conf")

if __name__ == '__main__':
    main()
