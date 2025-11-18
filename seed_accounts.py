import logging
import os
import sys

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_accounts():
    db = Database()
    
    # These are the EXACT accounts you provided. 
    # I have cleaned them to remove any accidental spaces or newlines.
    accounts_to_add = [
        ("918250687793", "BQG-IzsANRUcvcnQFuvbKwft-2u9VwLbxhuLcGAvEafq7y9Kuc2pjxFWeaI-FH4eUI06O0mowBcFPcuwNr99-SqcRtV1Kp1m6-nXC3adkWZP8zNw7PiDriFD-G6BLnTd5uuYzVLxwVhAKatR88savWzTKxW4ppDdLe9nwyx7DOrRWm-clf12TbpGG7xhdZILQIRvaO1hQuv4AqtRbW-HCwxPVB_e-0F7MS3f3vcKGIs9zgSK_-92cA2kKBIrjC3DvrIXFJiNcR0d9DrxJs7kb4FHnqeIkJ6NCuXXT_2TZ8iMZZe87WT7DHosiVUsyY3ZHNNZcj6WcjFNivqEXz1RztruYckYhwAAAAG9HI2wAA"),
        ("+918217231237", "BQG-IzsAGcPjqEozKvuN4sHpHJX-TJ9KfI_F8KcryMetEK0ClrSnNv4qGw4zcyotK5kdrfFNtyexMIXrsqE6X01A1DiTwV9x9ZOGyYn-5G5CiUrlNO8RsgcyF2HgMC0dcmVzitojv69Ny1nHHNe7gNsRYHorDyWEiBx2QrvaiR5cvZUzDTqF6RlKtMofll6K5rGQyEc48cwSOBcNZBhlYjikE7prEy81zod0lzE-q_OgBsIHalzwA-UnNURKiAFRckWjGtpLuUDE8SKr1oM_HaXjUHj9F_0c9G9HKaNrpY9zmi_J_fQCZ-dQEwdBvdIJXOQLKgNKuPMh_bDVDC1XiM2WQEmbkwAAAAF2UmBoAA"),
        ("917012660185", "BQG-IzsAIrPPYlccZM_9KAzDKJq18CJkOb81yCf5vZv49mgkG-mZsKjzx-NRojWGS617Sd2a7Hszh4BjAJz_IqPbeL_ZlCAb3M893f99ncflBgN5ES-nTSE5LgWYUlUpdVqD2SSOchZnNtXtXoKrAEGrhhO3GO8OUIGyjjXgwKjMQZx70Pgd4ZQLdDQIvzusXe4EiAshkuVVKQ5HXm5qZxYvlnP_-osD3EsQZR427DmlzOXEJezpcgByCQYD62rvNL2jbVjqF65rAcIQXHq0gE6lU4OhqHz8uEyZvdf-8dm2clVOSMXN-QOQmXglN-ODlUJcyCXPVPeAPWxHeve7ZDWqF6Q5gAAAAABD2rPAAA"),
        ("918265066933", "BQG-IzsAQwNZT2OZwNfhx40MrHEtSGOVDsFUVd8B7iHJbxNkChKpbiwqdUsJrt74AaBNMB2i7RgGo-BRaevVpTInuoLTVNMGNqxMAoptHBCxQ9uqZZP6y2-DGnWEwO4zRKw87UyHF4cWLxIve4Ef00yECXj4913T5y6_wewMkkNYZmpADmHf5hYOZh22gehwLbOmR82cgBSXdllajhtL7DGQBr3ABoHN6NixWohq1EPbw83bR2CRne48UNyR8DJ860teg3i6T2-KEAwhC4GIb1Si1nnN-91D2kOj7j2X4BIzLj3HBGS_QIVdSCKUFv7sqcoZjGBZWVocVyzXQPWZq7fgZpXTYgAAAAHMRDcpAA"),
        ("918237823721", "BQG-IzsAROPawXJ8hinmJ-sYdBSWktnmOHq9J9EcZxQcMFpPMpvYn_V_fRfssgbfEwcAOrLWvrjkvoXTYXaKHGUb6HGM4hYA5tQjH_KpKzEN_Zm11Oio__GfxeBIN6GNqXvVcWW7p4AWmRsjulylbFd6CLGLIid7ZnlrLYth9OFF5Q5wPnaw5Dhm5osPmttT6_5lbC2L-DlpnXCFnfe9cpSYIMw4NSAjYZTRoeflbOSOAFTysUcX70UTfmoSR6pnuEy1l2VDPw5VZ1pVCFYdkhcEsVj_X8VHa7wDw11kWkUBxIY_9AI0bidVe7i-Vw2CnosWu4SNHINarO9bOHaUO5xPmk_WZQAAAAF3zTLWAA"),
        ("918280808004", "BQG-IzsAgW6FA7iLUQV1byQPFlkcZu_iljKEoMz9L5us3VvPhp_qHYwBHdPjZr7R3B46AoVkV9eOYl19_rLk8jxgR-VYNlDQSxtEenZKNxrYYxoaqhQcqfp9AvkY926_5SksdJdgLkJ59X6wdNqpq8_bBzInr7B6nKmrblnZs3X8-nQOuDQTUs-JwjqiHIEQ44WisZG2aHMVaZxdRNuplgI6MQVtUgic9tvJAyzpVwnlFr2VUsVnnyMiNpWGef8kfVSygZN6WibXIFKCusGK1GaZlie-wmKMpNM3IXNe87PtHQR_-W6GM7dGrOHKiRj3Ln2MlJtZSqLxOPpBDVERoV8IMOOqWQAAAAGXdumVAA"),
        ("918186972777", "BQG-IzsAP-3tHIQkzgLxfv2WruMUrcjcqofm1ecGIAHFkOo254rMOzn_cN2czWfcZJ9-AxRJj-oOKP8XMMlBHBqTYC-Ic5I_UBEDOosG9MaaMfvoArjOVW6_82nrM9vuvkFmaXhVLHcJJ7L5EsBiJ02ZRB_xwrSYFHL69lTZyslolSEAL-51-pVS84FjE2HjvNoMjxnaG4OSWL9EXHQM_1maJTTf1A1N_GbnPpokEtOf-uWtNfrnXC1tl-fa9QERNySypHvurc404zIwm8o2NvIfm2_7lL41PX7NNmwST__iT6WfM_KrfooUoInvLcxR9yLGZmlpJLDIqzxz8tLLaCTtagTpRAAAAABglSlUAA"),
        ("918260962457", "BQG-IzsAYvtfeiYTgccsAnJw9NHXF-jq1lrfhRAP0WUHnmiYmLAovfaqcAON-2tpX6S-AERdqzRFST_ijJSNh0huBC4jY7aXL1JfQvQDKnsPE16GPn9OhjZjjsdXBuFWCMw3ZR8kTi-jmZIZmoBRKHFFU7dhO-zN-185j9AulpE5gAYBJxGVJjYL-eXaguQp5fjAHdSruAbCS9dXLQJ7U-N9pSjHNmo3E4CSJJgnm_Vdp-6o-lv2bkS7BpXOL4S3Q3jJ6XMLZIgDWsbnL0k0mgnJQiPKVZOKqh2ivxI7A7zTzaWA9AQaXALdW2tjink5S_MIYcTsD7fDkrWhi44_JMgwWZr2mQAAAAF0aGjFAA"),
        ("918220190406", "BQG-IzsAmtpJwWa-aVx6Z2u91BIZiNAYEFdJbaAiGgYsu_Q9drpKo1mzU8AqETJtSi0AdC8gYYmK1cypVVX_c6T0SqBlSfQrCj2q6MLZQoydEE0_5Xs9DHhhMjwg-kt9OxKi3KM_cIBphb4PN6kmwPDoVaHOQgmYE4yFBp56zMwtnGWWh5XSS3iNk9qxBU3xukHxHHndJeVtM_TqaxTI-ico5kbSAHecXA6FyzOUpYzxvXvCxXkhlZCzCi0V-pQrpX1LZTkeyWu5rdUkaJGkB4JA4ngRK_NGlQIuGeIXWkvZQOi3PeosvqQ9v7Ry4PQRtoulF_4Zsm4LqR6gBqo6s-KhanMhXwAAAAF1HKX5AA"),
        ("918200043245", "BQG-IzsAjtrteB3Rb0fVCnl36QzVZlJujp1UaLFI3kH_6JNLjWduecUD3E_kPVSbpvqueu-VbghzwjcbshbpuFf-xk6HWreZD3enLz7VzLfMCJd7ob-VICQx57HKgHNSkT13tP7nbU2-OBbbKDGdMXzbFrkxZNhN_VlA3djUbWOf87u-tepcyG7XSWiqM-BpxHEcfFI3uyJqs5ncrnOjhSkZqNnXU__jxN7xf322x0CWMCZkj6P-t0emvVKn-SmVgY0PPzlGI6x8V6xISejiUEnFHUMpbmcyike0ArUrYosC_MglRPZ4QgMCbdJ9WUQGoLik7sBya4FJKIAR1iNfoB9rSAygiAAAAAGrv731AA"),
        ("918272074200", "BQG-IzsAtQGiV_3leTmIj9k5GC4GBczfWNLFhS7c6SPdunTEpFcfkXZQY4F3nPrz1-sYoPsdP0wf7oe1zSzk3Sv7ru61Z2kM-Xc5tPayhHW8D5UlY7GDYMQgURZbDiNB7SJ2jFCnlfgoNsmmOBK2j2IPqACskjSPtGoIA9X6JQ_NXSYYMZd-bsw5IFxShJMaYtcMml8Uc6RMS6wgMTqrw59L3v3Npj9U0qPxOME5kaWynl0cuOc84l5dM-HDjYVcVIrYTsutH0kzyYx9f6TOhgcnECHbQkg2YTCJo8D8Bnz0ijRfZQrW-YP9ghPwxSe1j7mnM4iuHG6LttesCAJbc68SCqxn_AAAAAHtEVIIAA"),
        ("918217240245", "BQG-IzsAjYvtpUVVk0NRs2U0Alu2T8wS1209Sk7iEFBDqcoqeS3oHnfgZKcGX6u0RgicIJ2vjsWTyOHdFe2IbY3sb3xf32QXQUB4V7ZRvs3MT1FjtQ94hucX56iDQDKgrjacg2B6haR01l7CE74jlHIhL2vNpJ9wJLxY4473F2Ho7qFoiKKbfjJZPlBBYPJ7mIaSaJxTLtwJRWZ_GVC0bjxx6JLnF0Iks76fYWgeOlp8a2wSWHI66OLttSQwb482iiii1jl8M0qsd-SwaewD99ItwUWxpulh78yb9V3-QVxiEks9avToSg8eC1rP7_5aq3B2Hb50TVlsrf1hfPsViuFIns17TQAAAAGdvX_kAA"),
        ("918200928412", "BQG-IzsAssscDJkfMMctZ8DIck0T01hbnnCTkkjM4EZDnoNYPrV2dIvtTTiHhGNuMKOkdWKvjZfdcCNvFka_D_1JFmIs3j5BYVrpWiMrqaENYxYVixf832wE0QOvOE5EOwJ01Gy1r2GJYcLjsK57xmucA4rnqEiW-Ec5XLTovHaDmQQXwForIe34BA9kcozbS_VGV2OVBEF9pKIfAIJoQMiM4XFdrcEkoVCQzmlbjEKv7SqPatkOl_3AUzHiyl5MUNC38BugOgnFD1TUdyh7LOzCXMZTOG4brG90YqyLl8IGdKa_fitVRhBhfwIg6fDWE7pVUM2l1B9f60V0L7aYh7WVqKdUNQAAAAFoeb9ZAA"),
        ("918209455561", "BQG-IzsAmErXYl8baL8CBtuxR9rdpWIXa2wtXaNkAsP0DRwcZl7jr7nx5zLGrTnjdMCjJMpu9ewuCI2fepf18MEN6_AH4Rg-gw7XePhkE3Ggts_RlXJtlWNQWOLgnpc1vi5rAgKObR4AzCEIJGyNb9Hk78BspeOCqhboIs2hiRSB8Ut00XXDmijUIEly-Z_eUXSTe3QXeP0Cx5GHuIgxAW8lrrE_SXD3g-Z7JtBZO5zWYDrHcVJ5CgH69BPii1k4hHYftbcRjiCNwEYF0HakzuI3Wf9ou2qX-GSxiY26fHTpIw_vvAt_VK615Z589fb4O3PuF474KTmH5iIfVx-6qCyb77pcggAAAAHYX2liAA"),
        ("918235067013", "BQG-IzsArVbPaNkfKklRsponCAYdngQXvK8nnf373zEvgIiPeiBTLA5J70-0a5mNA9cCC4qenDUD150-1Lj5c9tzyVL9LOV0etlZbivXtnpAA6q3kSK6kiVZtSviLqYlCbXXjLNqZH_sR7eHCNUczdYUFXFBgP3Hzqvc9L5Aien_kPGUiwKc3ImPQF0QTwIRnYQXZ14uCI0NPVajQR-LOQ68qD4GF0bfENy4PWil9AoaMbMSqxvnt63K1oMdveVA-nt95s4FJxtWOU9x5UTFN5JNePTf7qvyrTS1omTFfDnNb23PbwdEYc_6vvLBaYdzlyQEsP_tC-rt5RpFJlNaynyLz8NBHwAAAAGkW3DcAA"),
        ("918262988781", "BQG-IzsAmNnJyXISvXns5NpKzLBsE_7_1kyT558ZE6EcTgRWVGJlzh-U76nsZ_l4GcFLBZOB7c6LN7gvHuzP3FRyTt3tbyjzGt71rfIPACS4hLrdzf-hfwlBhVM3FXF_FpgsKZVZTIqh3UuF7TbjIRWkgacT8nKbMu_N9t1QsdLqR2PKm23tEcXdnncKCxYECM6O5bPx4NNew2eUBNXKRiG_sGejRXU8-9L86qeEB7_8rPukFP4d1CNVT8WQsUap3ap1CYOxD3VCIRuEgJSxu8oUk6SWyDRSnRyYry1qt9K86jm_-4EAhx9QA6d_RqIMUNhfSjQ9c4zbgzaU-vcvhSCDfYr-WwAAAAHffyUcAA"),
        ("918270313375", "BQG-IzsApPj91a0fp-oIypZpeBAkW_6bHYlpau5jszJKxPq03GFIqOc_nNmzN_DfEH_iLo3SzLQy5LZCxGM0vJ4IAW8th9VNjg-yn3_E54D7Lfg1uh0XRYwDSNRO0R7jCc3_LmzkLw742wJIxES17EqAAr9DH_Sz9UKa58pQl8ire1kh4YBbvgeD955-la4pFL0JKicY-ViycaI6cKBKePRX_Sx-3tPdOFBd0ATi3OIwYI7qbFiD1axQUnHTxlnmYck6F4p9J7LCcngz7wmVTc7piWVMobQtlIEVBFuL69EWmiTFKJBmusAxwoVI1PZ0Lh5N6mNlAcgF0_Kc65A4crE57ji0iAAAAAFSz_jBAA"),
        ("918281592533", "BQG-IzsAXuG4QCI_Y9jrisa_r2MpgiXmNdfzKxUXIkHss72gnZhNYllrkrkntlsJ77cXdS0PNpJyZh6KqQiH2c_2qBGMXGCNf89_w2L3p5ISGDBGJ1ctyh7flRjbmqgmHezrikL0JQLZ2nXQ8hvPQtBrU6CmXyS-vr89jQGkMSTAchgYq4bWHYCESSuhvZQfs5VYtTUWNY5-JPzITtK4S2Jq98bIUNvAytt9R_C7I5CYQFHZIQ1vVElBtgOU-Iw5yOgY3K06opVq7hB0N6kzQvv-k6TJ7zovA-nykOnxUeEeN1S-Fp3nRoyuMkIgksmLdJDLu4hzNPNAuaidVd_sZ4mjUlau1gAAAAG6HcNuAA"),
        ("918208821367", "BQG-IzsAD_qdhvT9Lh-P0u8LvboNMOZ8wsvLcI4bazYsbSZFlQpi_c2Z4sFKSsTgcJ26CGbCXvWz9SAqB7C5WK7zyn7tqxhz7Lcg3MomdXXctTqcTeWA0PSo87lXUx47jnsER_QmtKZSHL2FbOlruiskc9cLV5Zyg15IYpL5cVpQ6i1UAs9LOMz9BDgTDWO4PA7lN2X0YdxrruMtU-zhnlREcPyY7ostgagbH879C8kv3LdIz-MF3c2AK_WAWtSgP9xfmcQaZpq647-p2qUeLXWUQShALBwQMvM6yU8WgHJCEo-E_qqlOkzvBZ5403Z__BzxkbeSQ9VlCYbqRN1BG5xW6Oum9wAAAAGx6FxTAA"),
        ("+918177862609", "BQG-IzsAYUAwIagzuywa7MBjxo3m-3hXPSPodK_VtnlsY9IyrE_8UUo3wUBo6PB4fHyLIf3Vs1xfOPYXlfUZ0JktIAcIbJjwz3fiblpPlbmQ51WXlXxTkOSnkL0R_-goemtjvUfGne1acbKf-qFa-ZuM4f5iKDD90xgkxvEpz2dsXBWM7DdPVatDXfI-plu8K1dGFj4OhIEVf1drGqLBsAV1ac4ojWCtN6ty_x8TvgEQGKcJUxM9SFxbBRTqcI41ugfn9s8ARPahofoPOqYgY12n8AyBXv-ZFnoijF304udDhkepOFt-tgnRJmC9D5rAH3xyiBBkZ7Ui4_opeRGR9zmIF4PH6AAAAAHCVqbtAA")
    ]

    print(f"🚀 Starting bulk import of {len(accounts_to_add)} accounts...")
    
    success_count = 0
    for phone, session in accounts_to_add:
        try:
            # Clean up session string
            session = session.strip()
            
            # Use add_account_manual
            account_id = db.add_account_manual(phone, session)
            
            if account_id:
                print(f"✅ Added {phone} (ID: #{account_id})")
                success_count += 1
            else:
                print(f"⚠️ Failed to add {phone} (Duplicate?)")
                
        except Exception as e:
            print(f"❌ Error adding {phone}: {e}")

    print("\n" + "="*30)
    print(f"🎉 Import Complete!")
    print(f"✅ Successfully Added: {success_count}")
    print(f"❌ Failed: {len(accounts_to_add) - success_count}")
    print("="*30)

if __name__ == "__main__":
    seed_accounts()