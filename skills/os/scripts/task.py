#!/usr/bin/env python3
"""Optional single-task state and evidence checks. No commands, models or queues run.

Usage: python3 task.py --project PROJECT init SLUG --goal TEXT --accept R1=TEXT --input FILE
Evidence receipts are declarations: hashes detect drift, not truth or review independence.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

STATES = {'planned', 'active', 'blocked', 'done', 'cancelled'}
MODES = ('managed', 'plan', 'brainstorm', 'review', 'recover', 'direct')
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')


def local_path(root, name):
    rel = PurePosixPath(name)
    if not name or rel.is_absolute() or '..' in rel.parts or str(rel) != name or '\\' in name:
        raise ValueError(f'path must be project-relative: {name}')
    result = root
    for part in rel.parts:
        result = result / part
        if result.is_symlink(): raise ValueError(f'symlink forbidden: {name}')
    return result


def sha(path):
    if not path.exists(): return None
    if not path.is_file(): raise ValueError(f'expected a file: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root, names):
    return {name: sha(local_path(root, name)) for name in names}


def validate(data, allow_unsupported_mode=False):
    if not isinstance(data, dict) or data.get('schema') != 1 or data.get('state') not in STATES:
        raise ValueError('invalid task schema/state')
    mode = data.get('mode')
    if (not isinstance(mode, str) or not ID.fullmatch(mode)
            or (mode not in MODES and not allow_unsupported_mode)):
        raise ValueError('unsupported task mode; preserve the file and explicitly review migration to a supported mode')
    if (not ID.fullmatch(data.get('id', '')) or not data.get('goal')
            or not isinstance(data.get('revision'), int) or data['revision'] < 0
            or not isinstance(data.get('independent_review'), bool)):
        raise ValueError('invalid task fields')
    if not isinstance(data.get('inputs'), list) or not data['inputs'] or not all(isinstance(n,str) for n in data['inputs']):
        raise ValueError('task requires explicit input file scope')
    criteria = data.get('criteria')
    if not isinstance(criteria, dict) or not criteria: raise ValueError('task requires acceptance criteria')
    for name, item in criteria.items():
        if not ID.fullmatch(name) or not isinstance(item, dict) or not item.get('description'):
            raise ValueError('invalid criterion')
        receipt = item.get('receipt')
        if receipt is not None:
            validate_receipt(receipt)
    if data.get('review') is not None:
        validate_receipt(data['review'])
        if not data['review'].get('reviewer') or data['review'].get('verdict') not in ('passed','changes_required'):
            raise ValueError('invalid review declaration')
    return data


def validate_receipt(receipt):
    if not isinstance(receipt, dict) or receipt.get('result') not in ('passed','failed','not_run'):
        raise ValueError('invalid evidence result')
    if receipt.get('kind') not in ('executed','static','independent') or not receipt.get('summary'):
        raise ValueError('invalid evidence kind/summary')
    if not isinstance(receipt.get('inputs'), dict) or not isinstance(receipt.get('evidence'), dict) or not receipt['evidence']:
        raise ValueError('invalid evidence snapshot')
    for name, value in list(receipt['inputs'].items()) + list(receipt['evidence'].items()):
        if not isinstance(name, str) or (value is not None and not re.fullmatch(r'[a-f0-9]{64}', value)):
            raise ValueError('invalid evidence hash')


def load(path, allow_unsupported_mode=False):
    return validate(json.loads(path.read_text()), allow_unsupported_mode)


@contextmanager
def write_lock(path):
    lock = path.with_suffix('.lock')
    local_path(path.parent, lock.name)
    try: fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError(f'task locked: {lock}; inspect owner before manual recovery')
    try:
        with os.fdopen(fd, 'w') as stream: stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def save(path, data):
    validate(data)
    local_path(path.parent, path.name)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.task-', delete=False) as stream:
            temp = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists(): temp.unlink()


def receipt_issues(root, data, receipt):
    if receipt is None: return ['missing evidence receipt']
    issues = []
    if receipt['result'] != 'passed': issues.append('result not passed')
    current = snapshot(root, data['inputs'])
    if receipt['inputs'] != current: issues.append('input scope or content changed')
    for name, expected in receipt['evidence'].items():
        actual = sha(local_path(root, name))
        if expected is None or actual != expected: issues.append(f'evidence changed/missing: {name}')
    return issues


def inspect(root, data):
    issues = {}
    if data['mode'] not in MODES:
        issues['mode'] = ['unsupported task mode; read-only inspection, explicit migration review required']
    for name, item in data['criteria'].items():
        found = receipt_issues(root, data, item.get('receipt'))
        if found: issues[name] = found
    if data['independent_review']:
        review = data.get('review')
        found = receipt_issues(root, data, review)
        if review is not None and review.get('verdict') != 'passed': found.append('review not passed')
        if found: issues['independent_review'] = found
    return {'id': data['id'], 'state': data['state'], 'revision': data['revision'],
            'ready_to_finish': not issues, 'issues': issues,
            'evidence_semantics': 'declared results and file integrity; not proof of truth or independence'}


def make_receipt(root, data, args):
    evidence = snapshot(root, args.evidence)
    if not evidence or any(value is None for value in evidence.values()):
        raise ValueError('all evidence files must exist')
    if not args.summary.strip(): raise ValueError('summary required')
    return {'result': getattr(args, 'result', 'passed'), 'kind': getattr(args, 'kind', 'independent'),
            'summary': args.summary, 'inputs': snapshot(root, data['inputs']), 'evidence': evidence}


def operate(args):
    root = args.project
    if root.is_symlink() or not root.is_dir(): raise ValueError('project must be an existing non-symlink directory')
    root = root.resolve()
    if not ID.fullmatch(args.slug): raise ValueError('invalid task slug')
    path = local_path(root, f'.adas-assist/tasks/{args.slug}/task.json')
    if args.command == 'status': return inspect(root, load(path, allow_unsupported_mode=True))
    path.parent.mkdir(parents=True, exist_ok=True)
    with write_lock(path):
        if args.command == 'init':
            if path.exists(): raise ValueError('task exists; init never overwrites')
            manual = local_path(path.parent, 'TASK.md')
            if manual.exists(): raise ValueError('manual TASK.md exists; choose one task state source')
            criteria = {}
            for entry in args.accept:
                name, sep, text = entry.partition('=')
                if not sep or not ID.fullmatch(name) or not text.strip() or name in criteria:
                    raise ValueError('acceptance must be unique ID=description')
                criteria[name] = {'description': text, 'receipt': None}
            snapshot(root, args.input)
            if path.relative_to(root).as_posix() in args.input: raise ValueError('task state cannot be an input')
            data = {'schema':1, 'id':args.slug, 'goal':args.goal, 'mode':args.mode,
                    'state':'planned', 'revision':0, 'scope':getattr(args, 'scope', 'current user task authorization'),
                    'inputs':list(dict.fromkeys(args.input)),
                    'criteria':criteria, 'independent_review':args.independent_review,
                    'review':None, 'reason':None, 'next':args.next}
        else:
            data = load(path)
            command = args.command
            if command == 'start' and data['state'] == 'planned': data['state'] = 'active'
            elif command in ('record','review') and data['state'] == 'active':
                receipt = make_receipt(root, data, args)
                if command == 'record':
                    if args.criterion not in data['criteria']: raise ValueError('unknown criterion')
                    data['criteria'][args.criterion]['receipt'] = receipt
                else:
                    if not args.reviewer.strip(): raise ValueError('reviewer identity/source required')
                    receipt.update(reviewer=args.reviewer, verdict=args.verdict)
                    receipt['result'] = 'passed' if args.verdict == 'passed' else 'failed'
                    data['review'] = receipt
            elif command == 'finish' and data['state'] == 'active':
                if inspect(root, data)['issues']: raise ValueError('finish blocked: missing, failed or stale evidence/review')
                data['state'] = 'done'
            elif command == 'block' and data['state'] == 'active': data['state'] = 'blocked'
            elif command == 'resume' and data['state'] == 'blocked': data['state'] = 'active'
            elif command == 'reopen' and data['state'] == 'done': data['state'] = 'active'
            elif command == 'cancel' and data['state'] in ('planned','active','blocked'): data['state'] = 'cancelled'
            else: raise ValueError(f'invalid transition: {data["state"]} -> {command}')
            if hasattr(args, 'reason'):
                if not args.reason.strip(): raise ValueError('reason required')
                data['reason'] = args.reason
            if hasattr(args, 'next'): data['next'] = args.next
            data['revision'] += 1
        result = inspect(root, data)
        save(path, data)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('slug')
    init.add_argument('--scope', default='current user task authorization')
    init.add_argument('--goal', required=True); init.add_argument('--mode', choices=MODES, default='managed')
    init.add_argument('--accept', action='append', required=True)
    init.add_argument('--input', action='append', required=True)
    init.add_argument('--independent-review', action='store_true'); init.add_argument('--next', default='')
    for command in ('status','start','finish','block','resume','reopen','cancel','record','review'):
        cmd = sub.add_parser(command); cmd.add_argument('slug')
        if command in ('block','resume','reopen','cancel'): cmd.add_argument('--reason', required=True)
        if command in ('block','resume','reopen'): cmd.add_argument('--next', required=True)
        if command in ('record','review'):
            cmd.add_argument('--evidence', action='append', required=True); cmd.add_argument('--summary', required=True)
        if command == 'record':
            cmd.add_argument('--criterion', required=True)
            cmd.add_argument('--result', choices=['passed','failed','not_run'], required=True)
            cmd.add_argument('--kind', choices=['executed','static'], required=True)
        if command == 'review':
            cmd.add_argument('--reviewer', required=True)
            cmd.add_argument('--verdict', choices=['passed','changes_required'], required=True)
    try:
        print(json.dumps(operate(parser.parse_args()), ensure_ascii=False)); return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
