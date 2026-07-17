"""pytest test suite for the repository intelligence parsers.

Test categories
---------------
- Python parser
- TypeScript parser
- JavaScript parser
- Go parser
- Rust parser
- Error recovery (malformed files)
- Symbol ID determinism and format

All tests are fully deterministic (no randomness, no I/O).
"""

import pytest
from app.services.intelligence.parsers import parse_file, supported_extensions, get_language
from app.services.intelligence.parsers.python_parser import parse as py_parse
from app.services.intelligence.parsers.typescript_parser import parse as ts_parse
from app.services.intelligence.parsers.javascript_parser import parse as js_parse
from app.services.intelligence.parsers.go_parser import parse as go_parse
from app.services.intelligence.parsers.rust_parser import parse as rs_parse


# ===========================================================================
# Helpers
# ===========================================================================

def _syms(result, sym_type=None):
    s = result["symbols"]
    if sym_type:
        s = [x for x in s if x["type"] == sym_type]
    return s

def _sym_names(result, sym_type=None):
    return [s["name"] for s in _syms(result, sym_type)]

def _imp_modules(result):
    return [i["module"] for i in result["imports"]]


# ===========================================================================
# Python parser
# ===========================================================================

class TestPythonParser:
    SOURCE = """\
import os
from typing import List, Optional

MY_CONST = 42
ANOTHER_CONST = "hello"

class UserService:
    def __init__(self): pass
    def get_user(self, uid: int): pass
    def _private_method(self): pass

def top_level_function(x: int) -> int:
    return x * 2

async def async_fn():
    pass
"""

    def test_language(self):
        r = py_parse(self.SOURCE, "app/service.py")
        assert r["language"] == "python"

    def test_file_path(self):
        r = py_parse(self.SOURCE, "app/service.py")
        assert r["file_path"] == "app/service.py"

    def test_detects_class(self):
        r = py_parse(self.SOURCE, "app/service.py")
        assert "UserService" in _sym_names(r, "class")

    def test_detects_methods(self):
        r = py_parse(self.SOURCE, "app/service.py")
        methods = _sym_names(r, "method")
        assert "__init__" in methods
        assert "get_user" in methods
        assert "_private_method" in methods

    def test_detects_top_level_functions(self):
        r = py_parse(self.SOURCE, "app/service.py")
        assert "top_level_function" in _sym_names(r, "function")
        assert "async_fn" in _sym_names(r, "function")

    def test_detects_imports(self):
        r = py_parse(self.SOURCE, "app/service.py")
        modules = _imp_modules(r)
        assert "os" in modules
        assert "typing" in modules

    def test_visibility_private(self):
        r = py_parse(self.SOURCE, "app/service.py")
        priv = [s for s in r["symbols"] if s["name"] == "_private_method"]
        assert priv and priv[0]["visibility"] == "private"

    def test_visibility_public(self):
        r = py_parse(self.SOURCE, "app/service.py")
        pub = [s for s in r["symbols"] if s["name"] == "UserService"]
        assert pub and pub[0]["visibility"] == "public"

    def test_symbol_id_format(self):
        r = py_parse(self.SOURCE, "app/service.py")
        cls = [s for s in r["symbols"] if s["name"] == "UserService"][0]
        assert cls["id"] == "py:app/service.py:UserService:class"

    def test_symbol_id_hash_present(self):
        r = py_parse(self.SOURCE, "app/service.py")
        for s in r["symbols"]:
            assert "id_hash" in s and len(s["id_hash"]) == 64

    def test_line_end_geq_line_start(self):
        r = py_parse(self.SOURCE, "app/service.py")
        for s in r["symbols"]:
            assert s["line_end"] >= s["line_start"]

    def test_syntax_error_returns_empty(self):
        r = py_parse("def broken(:", "bad.py")
        assert r["symbols"] == []
        assert r["imports"] == []


# ===========================================================================
# TypeScript parser
# ===========================================================================

class TestTypeScriptParser:
    SOURCE = """\
import { useState, useEffect } from 'react';
import type { FC } from 'react';
export { default as Button } from './Button';

export interface IUser {
  id: string;
  name: string;
}

export type UserId = string;

export enum Status {
  Active = 'active',
  Inactive = 'inactive',
}

export class UserService {
  private readonly db: DB;
  async getUser(id: string): Promise<IUser> { return {} as IUser; }
}

export function fetchUser(id: string): Promise<IUser> {
  return Promise.resolve({} as IUser);
}

export const MAX_RETRIES = 3;
"""

    def test_language(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert r["language"] == "typescript"

    def test_detects_interface(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "IUser" in _sym_names(r, "interface")

    def test_detects_enum(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "Status" in _sym_names(r, "enum")

    def test_detects_type_alias(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "UserId" in _sym_names(r, "type_alias")

    def test_detects_class(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "UserService" in _sym_names(r, "class")

    def test_detects_function(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "fetchUser" in _sym_names(r, "function")

    def test_detects_constant(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "MAX_RETRIES" in _sym_names(r, "constant")

    def test_exported_visibility_public(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        cls = [s for s in r["symbols"] if s["name"] == "UserService"][0]
        assert cls["visibility"] == "public"

    def test_import_deduplication(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        modules = _imp_modules(r)
        # 'react' appears twice (import + import type) → should appear once
        assert modules.count("react") == 1

    def test_export_from_captured(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        assert "./Button" in _imp_modules(r)

    def test_symbol_id_format(self):
        r = ts_parse(self.SOURCE, "src/user.ts")
        iface = [s for s in r["symbols"] if s["name"] == "IUser"][0]
        assert iface["id"] == "ts:src/user.ts:IUser:interface"


# ===========================================================================
# JavaScript parser
# ===========================================================================

class TestJavaScriptParser:
    SOURCE = """\
const express = require('express');
import { helper } from './utils';

export class App {
  start() {}
}

export function createApp() {
  return new App();
}

export const VERSION = '1.0.0';
"""

    def test_language(self):
        r = js_parse(self.SOURCE, "src/app.js")
        assert r["language"] == "javascript"

    def test_id_prefix_is_js(self):
        r = js_parse(self.SOURCE, "src/app.js")
        for sym in r["symbols"]:
            assert sym["id"].startswith("js:")

    def test_detects_class(self):
        r = js_parse(self.SOURCE, "src/app.js")
        assert "App" in _sym_names(r, "class")

    def test_require_captured(self):
        r = js_parse(self.SOURCE, "src/app.js")
        assert "express" in _imp_modules(r)


# ===========================================================================
# Go parser
# ===========================================================================

class TestGoParser:
    SOURCE = """\
package main

import (
    "fmt"
    "net/http"
)

type Server struct {
    port int
}

type Handler interface {
    Handle(r *http.Request)
}

func NewServer(port int) *Server {
    return &Server{port: port}
}

func (s *Server) Start() error {
    fmt.Println("starting")
    return nil
}

func (s *Server) stop() {
}
"""

    def test_language(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        assert r["language"] == "go"

    def test_detects_struct(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        assert "Server" in _sym_names(r, "struct")

    def test_detects_interface(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        assert "Handler" in _sym_names(r, "interface")

    def test_detects_function(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        assert "NewServer" in _sym_names(r, "function")

    def test_detects_method(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        methods = _sym_names(r, "method")
        assert "Start" in methods
        assert "stop" in methods

    def test_go_visibility(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        start = [s for s in r["symbols"] if s["name"] == "Start"][0]
        assert start["visibility"] == "public"
        stop = [s for s in r["symbols"] if s["name"] == "stop"][0]
        assert stop["visibility"] == "private"

    def test_block_imports_captured(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        modules = _imp_modules(r)
        assert "fmt" in modules
        assert "net/http" in modules

    def test_symbol_id_format(self):
        r = go_parse(self.SOURCE, "cmd/server.go")
        srv = [s for s in r["symbols"] if s["name"] == "Server"][0]
        assert srv["id"] == "go:cmd/server.go:Server:struct"


# ===========================================================================
# Rust parser
# ===========================================================================

class TestRustParser:
    SOURCE = """\
use std::io::{self, Read};
use std::collections::HashMap;
extern crate serde;

pub struct Config {
    pub host: String,
    port: u16,
}

pub(crate) enum Status {
    Running,
    Stopped,
}

pub trait Runnable {
    fn run(&self) -> io::Result<()>;
}

pub const MAX_CONNECTIONS: u32 = 100;

pub fn create_config(host: String) -> Config {
    Config { host, port: 8080 }
}

impl Config {
    pub fn new(host: String) -> Self {
        Config { host, port: 8080 }
    }

    fn validate(&self) -> bool {
        !self.host.is_empty()
    }
}
"""

    def test_language(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert r["language"] == "rust"

    def test_detects_struct(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert "Config" in _sym_names(r, "struct")

    def test_detects_enum(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert "Status" in _sym_names(r, "enum")

    def test_detects_trait(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert "Runnable" in _sym_names(r, "trait")

    def test_detects_constant(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert "MAX_CONNECTIONS" in _sym_names(r, "constant")

    def test_detects_function(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert "create_config" in _sym_names(r, "function")

    def test_detects_methods(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        methods = _sym_names(r, "method")
        assert "new" in methods
        assert "validate" in methods

    def test_pub_visibility(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        cfg = [s for s in r["symbols"] if s["name"] == "Config"][0]
        assert cfg["visibility"] == "public"

    def test_private_visibility(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        validate = [s for s in r["symbols"] if s["name"] == "validate"][0]
        assert validate["visibility"] == "private"

    def test_use_imports_captured(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        modules = _imp_modules(r)
        assert any("std::io" in m for m in modules)
        assert any("std::collections" in m for m in modules)

    def test_extern_crate_captured(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        assert "serde" in _imp_modules(r)

    def test_symbol_id_format(self):
        r = rs_parse(self.SOURCE, "src/config.rs")
        cfg = [s for s in r["symbols"] if s["name"] == "Config"][0]
        assert cfg["id"] == "rs:src/config.rs:Config:struct"


# ===========================================================================
# Error recovery
# ===========================================================================

class TestErrorRecovery:
    def test_python_syntax_error_returns_empty_not_exception(self):
        r = py_parse("class Broken(:", "bad.py")
        assert isinstance(r, dict)
        assert r["symbols"] == []
        assert r["imports"] == []

    def test_typescript_malformed_returns_dict(self):
        r = ts_parse("export class {{{ }", "bad.ts")
        assert isinstance(r, dict)

    def test_go_empty_file_returns_empty(self):
        r = go_parse("", "empty.go")
        assert r["symbols"] == []
        assert r["imports"] == []

    def test_rust_empty_file_returns_empty(self):
        r = rs_parse("", "empty.rs")
        assert r["symbols"] == []
        assert r["imports"] == []

    def test_parse_file_unknown_extension_returns_empty(self):
        r = parse_file("file.xyz", "some content")
        assert r["language"] == "unknown"
        assert r["symbols"] == []
        assert r["imports"] == []


# ===========================================================================
# Dispatcher and versioning
# ===========================================================================

class TestDispatcher:
    def test_supported_extensions_contains_all_languages(self):
        exts = supported_extensions()
        assert ".py" in exts
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".js" in exts
        assert ".jsx" in exts
        assert ".go" in exts
        assert ".rs" in exts

    def test_get_language_python(self):
        assert get_language("main.py") == "python"

    def test_get_language_typescript(self):
        assert get_language("App.tsx") == "typescript"

    def test_get_language_go(self):
        assert get_language("main.go") == "go"

    def test_get_language_unknown(self):
        assert get_language("README.md") == "unknown"

    def test_symbol_id_deterministic(self):
        r1 = py_parse("class Foo:\n    pass\n", "a/b.py")
        r2 = py_parse("class Foo:\n    pass\n", "a/b.py")
        ids1 = {s["id"] for s in r1["symbols"]}
        ids2 = {s["id"] for s in r2["symbols"]}
        assert ids1 == ids2
