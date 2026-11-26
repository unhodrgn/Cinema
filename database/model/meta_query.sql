-- 모델 파일(gen_drawio.py)의 입력. 마이그레이션 0001~0005를 적용한 빈 DB에서 실행하고
-- 결과(JSON 한 줄)를 meta.json 으로 저장한다 (psql -At -f meta_query.sql).
select json_build_object(
 'columns', (select json_agg(json_build_object('t',c.relname,'n',a.attname,'type',format_type(a.atttypid,a.atttypmod),'notnull',a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),'ident',a.attidentity,'ord',a.attnum) order by c.relname,a.attnum)
   from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
   where n.nspname='public' and c.relkind='r' and a.attnum>0 and not a.attisdropped),
 'constraints', (select json_agg(json_build_object('t',c.relname,'name',k.conname,'type',k.contype,'def',pg_get_constraintdef(k.oid)) order by c.relname,k.contype,k.conname)
   from pg_constraint k join pg_class c on c.oid=k.conrelid where k.connamespace='public'::regnamespace),
 'indexes', (select json_agg(json_build_object('t',tablename,'name',indexname,'def',indexdef) order by tablename,indexname) from pg_indexes where schemaname='public'),
 'triggers', (select json_agg(json_build_object('t',c.relname,'name',t.tgname) order by c.relname,t.tgname) from pg_trigger t join pg_class c on c.oid=t.tgrelid where c.relnamespace='public'::regnamespace and not t.tgisinternal)
);
