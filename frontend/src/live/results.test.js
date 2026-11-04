import {test} from 'node:test';
import assert from 'node:assert/strict';
import {resultView} from './results.js';
test('result values and labels never become executable HTML',()=>{
 const html=resultView({'<script>':'<img src=x onerror=alert(1)>',items:[{source:'<b>unsafe</b>',count:1}]});
 assert(!html.includes('<script>'));assert(!html.includes('<img'));assert(html.includes('&lt;img'));assert(html.includes('<dl'));assert(html.includes('<table'));
});
test('typed answer and rehearsal views are readable, not JSON',()=>{
 assert(resultView({answered:true,answer:'Alice owns payments',citations:[]}).includes('Evidence found'));
 assert(resultView({assessment_type:'workspace_knowledge_coverage',score:.5,scenarios:2,eligible_scenarios:2,omitted_scenarios:0,results:[],missed_topics:[],readiness:'partly_ready'}).includes('50%'));
 assert(!resultView({stored:1,flagged:0}).includes('"stored"'));
});
