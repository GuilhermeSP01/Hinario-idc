import { test, expect } from '@playwright/test';

test('renumbering preserves identity, favorites and worship; UUIDs work and links remain numeric', async ({ page }) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('h3')).toHaveCount(236);
  await page.evaluate(async () => {
    const db=await new Promise((resolve,reject)=>{const request=indexedDB.open('HinarioIdcDB');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
    await new Promise((resolve,reject)=>{
      const tx=db.transaction('hymns','readwrite');const store=tx.objectStore('hymns');
      const existing=store.get('145');existing.onsuccess=()=>store.put({...existing.result,number:464,version:4});
      store.put({id:'51cfde53-5391-49fe-91ee-ecb8ee1e4bfa',number:465,title:'Novo Hino Editorial',version:4,
        sections:[{type:'verse',number:1,lines:['Verso de teste']}],deleted:false});
      tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);
    });db.close();
    for(const [key,value]of Object.entries({local_version:'4',favorite_ids:'["145"]',worship_ids:'["145"]',last_hymn_id:'145'}))
      localStorage.setItem('CapacitorStorage.hinario_idc_'+key,value);
  });
  await page.reload();await expect(page.locator('h3')).toHaveCount(237);
  const search=page.getByPlaceholder('Buscar por número, título ou trecho...');
  await search.fill('464');await expect(page.locator('h3')).toHaveText(['Rocha Eterna']);
  await search.fill('465');await expect(page.locator('h3')).toHaveText(['Novo Hino Editorial']);
  const result=await page.evaluate(async()=>{
    const {useHymnsStore}=await import('/src/stores/hymnsStore.ts');
    const {useFavoritesStore}=await import('/src/stores/favoritesStore.ts');
    const {useWorshipStore}=await import('/src/stores/worshipStore.ts');
    const {encodeWorshipSeed,decodeWorshipSeed}=await import('/src/services/worshipShare.ts');
    const store=useHymnsStore();
    const encoded=encodeWorshipSeed([464,465]);
    return {ids:store.resolveHymnIdsByNumbers(decodeWorshipSeed(encoded)),old:store.resolveHymnIdsByNumbers([145]),
      favorite:useFavoritesStore().isFavorite('145'),worship:useWorshipStore().worshipIds,selected:store.currentHymnId};
  });
  expect(result).toEqual({ids:['145','51cfde53-5391-49fe-91ee-ecb8ee1e4bfa'],old:[],favorite:true,worship:['145'],selected:'145'});
  expect(errors).toEqual([]);
});
