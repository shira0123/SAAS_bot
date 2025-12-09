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
    
    # List of (Phone, SessionString) tuples extracted from your input
    accounts_to_add = [
        ("918270313375", "1BVtsOHoBu30oz7ux9ZV0vpOkW-IE291i4qc7xAGfKTEncjTT1QAT98PUqYpbe87IWiNqWOP4dqvRzHAbGmu9aksM7A_gSuD4zHW36fjpUPGQOpNb3KokceWF_Uq5GTn_reJwLI6Uxd9dvWsjp5hp4QNzoYxtSTlpRpjqjcHUzP5p4_rcaaQ64SGk2VtU9IKuqK3dmck5PniDlTMDyoKpDssA-L9XMk1uvYqhqwnfdP6bjOtGkUiMKrnPepjQNSUR9sAPvRj6Ea-JuJ05eJMsfZcg9uvB_58je7r_u5WjREzkceJJfjHSKxkF3rQW0K7m7ctII2d2Ku4PbmhBp2v2N8Z_NZMd-qM="),
        ("918262988781", "1BVtsOHoBuwRodxnT8NZwQE96BCFOcUyk5CrLq8IZmzm1MnVJf1BQ6NNlZjOttFS2MH-RSMZu7yyuhJEKQIjVf3A42rKbo5ZMpofT-oCLLrtcFAgoDisiSHSC1KCVyrIVhYFUJPmG9B9_Pm2wPgbZRTN1YyBtKSPz0YTN4dO0TB7DL52PfTgrEHaa1ANvohvvOXFv4MUGvERJKvr7OFbdMgxsHCM5-fFt_NDZvwNxshDH8DsFt8l7haX2rtRJOwHtbjXxh7dxR3yrKazqcYzDfVqDfrKra6vHe8foGB36565a5drmLdR83eQ-udoZvS2cs0SzplBna2Itr8oq4kO71zzk-nSM7fU="),
        ("918235067013", "1BVtsOHoBu7PukdsEAR4wBmYiRAeETQWAt_WWll7NNIyAL3kI1PCwRypmWt7U3c5gCI98GMCsq3nfZGF_1w18AMrtSVjKWFtroq8Dux8SoNQTQR0y68jVpL-TeDfrGKMKUJ0iwKtKkIeKB1plh-YFFS9N5lwdeuoyu_r3oYTTEniYtwggsuhj_WKhNZxhNBkSwMpUMiS42zkuTW6BGExvwNNzCDYQavYe1rKgaw34O12aX-3twSS7syOaOp0CYtAV4AMx_GGYvnhGN8loaHEJz-DpsDHR1vlxPYxCpodxAzb1L9jpKZFcqvFXWqSy5RKEjaVi7XVBnZ1JiX_RMZc4n3b6uXyeylM="),
        ("918209455561", "1BVtsOHoBuxd_zo8Cl2cdQ_6sBLYJrB_fYH3wRXhTJTEWg_AKSPM8krIqcyvBH-mtUYErR8kgo9etHXfWtFvy92RpAsloT0HSpWLC8u0zuRskRnKf6mGm5lfEBtFKdcgCwHbaxkxrGsydWEYOQYhrle9Kbh8Sm-0-ghP0--uMvHZ9e4ChRGvqUpQz3tnBiJqeDnlwRVUFcuif3QXdGrXzO672MLK4XhTJtbDhL3oY8YZzh8YnkfpRWhyMYT8bXvLQFXOitgMwLkEPOCAHgIhiQsCY2bzDQmOkxcPJvU4BfKN3icE4WRj4NoDDmteC89VLVvCQHPyRlft6bNIiwRHOrF50gCfxz-U="),
        ("918200928412", "1BVtsOHoBuyi99pezrMkP4OSZR1fhsLgFIRTeP2riCdSGNbG62bIJhAJKgzjI0Qyq2grfQM-WBtpel4HWMH_VbX5zYLJ1jmpgqoF43FWfTFXZMyX3tMKRQ04FdlCeuiXqbyYFroDRc_CRVjOA_nMJKG2GHjKkNPYcYaD0enLC8lvomthhXzX-q1NrjAd2fg9KfqGBEcYrqiZOONolAteM3037zgDNa7XS7LIN9Te-jg5bPzs3Sg0roB3OhQ84xyPFPxfq12gGQUIkcm1yHSrpScPSVueqG2Lg9maJCMbn2MSq6aC_AT-FO1jCP83YTZhw4rw1R13mIOPKFxK8PEtDsjS8VGZov_s="),
        ("918217240245", "1BVtsOHoBu2j-DYrJTHKwa_vhHchzm497nXNhKuRMvjPZlnCgbB5T8TF4nzHc2fao5fsVDlpMD5tjIGp6Kh6IRAlNIagwMPtyUv2BgFTax3FFqumvV6JH6lZZtDk6MehaOj0JOlbWlKOTe1t__-pGjW3zCyNXKTQD1blTqQwFEQGyINQCz99mh6BthuF27XtF-nOOa2pKA68IEyTlLd_ilabLMBJIMd0PPiv34hw3r5IwRo_JMoFhFJmzOHybQYYVKLRNJL7FvsAVJrL3UeCzh4gbNNwGaCxysvpvkkpaK83FcXWVoVI9P54qfPI_x9kGpBLZT7BgO7aubCnfqQ2T0dHi3_EbAgQ="),
        ("918200043245", "1BVtsOHoBu5ChJmedivb6hJ6wtxCnulUdnGldrdjWG0XRwo0ik6pXhboa4EAmOtYiQyJTT1SXFcRjKqrmaP0Yahl2GfWcE8Zslr6DAsMDXu-QJnkRinD_QostoTz7l5529NzV3qhmDw9kzGBw9I69NBQKDqhIDBzkYvrOEmYTzeqgLyu8-YRrqul1jwanCB-LezP7hjAMSf1bIvVab0EwKNP7UTlBH4vWoxBL0VpASD5ehi8O1b7K4oWE-jSSbjUUmc_xg_ZVBr125GL4hD7xm6-ZAniK8eQloEZVqxv6UkZf0X5F9d_K1ooC5kemrckgwR1sSmTMC2jJxDYlOXX25tOzfB5-QeA="),
        ("918250687793", "1BVtsOHoBuzTRnJDqAsenSKtseVRmIrwjv29h3EOA5n8wrdAzMelfwy_5DxbBvZP3guGj1sPpRCH5g3CdbJWqGhwTI8qH-gEPWvjVEam-H2xVA6vh5FNBjfCe5YqIKM8m0Eo6kfVp3JfERNdrMFTTMYBS6wVzxz8e8JsMeXhsMXZS8dqAuwEdM8rss5f6nc44xb3n00kHEZXNncmnZ3nhiogpxb_Nkx_j0bk8aq7XoZLSkmQR__yJUh8Zd12WlUpRMo5rIUTIcqzhkEmJswMK7d0OwLKT3IgTHzfUGUr-jd4gdK3u7OQvLvns_s60Ok4RaNOnU2ysIV0Rog-J9ntbmYs2Rmq1mGU="),
        ("918217231237", "1BVtsOHoBu7JVIn_mrstw8GVUNL54UEJ3vFxEj3_NlipKeqt-MSf_PykMZ85Rvmwggi5ge-6cqJtSUdIE53dVra71yEajKCJ9Av9FoK1JeSjCmHvjefjvabLReos1HzAE_SnV-oeMRjPMV1Hb8H3VNfPGEhLmn3Q8-YyagOhnvFvpujyR-93xdtMToZbzHCJCKfBCY-cRLsPp2L4VHs6-OYJ_Pft1LCR2ESeosrka4miJuhKgzO9dfRNr_hu_K3jbOlX2vURywtzTppsWDjpmTNXd5zgX0-lyv_4z6cKi4wYCvzHAKKAwRqRpMMRupm0sNDct0PEH46eurGY130Hv-u5SLraY-d8="),
        ("917012660185", "1BVtsOHoBu2_Sv9Xv1GwltymXtp-uEc01hcrUPCwP3bRgkMYVD8dYgLUbitYqB8B2K3ffhLliEWKdhKXD9H7orhVteXCyYqj021mAYAF4_UJgCmrEd6dER7joYIkGcLkbKHpHsrTN6efE7aEhnx_VpRb5yByueiJu5BNkJ2XtY23G6LmUmnS8HQU8pNHUMe54PC4qiDCLjyOd85NjI7kQnBo3Y2RZ7P7hPFjOSIahVKHWh_L398ZiEJ1Tpfk6o1ELnz8BWHTGoCYdFtwmXA6hPImHH1-3IxsnWXgaJtQVB60_sv7TEwhflLDNJ2lZAnzDrTnrqpWszX5Rz-qGuIsuEjVBjRcAUbE="),
        ("918265066933", "1BVtsOHoBu3LynDU61dc9LsmWte3Ztbrpkf19cX_PIbjY02iR41ETDQo5-xEG3H-1z1KsYrHHvZdt_Rd9zZwPd8tbX_ugM22-qsaYQ0XIAQL4FQD2bo3L-pPFP21_pFgGI85EiZFA-nj89PRIiXKxCuKxWeJyix0j2gxRg3b61i29pQfWEqgqRGcN_Qnzi7SsmBZrafGKr7Q5v8Suxjs3VgZAjmusERXuHYnCoe7LWhQhmIev1yB6FlW82szrVXFE7Z4hUOptY4lnEL2X_Fcz4-xOggMq_5EDjEIDgwb4QfeInNaxFTyGxrAtfIpOtWnS_QJHL36Ov03JbTmUuYVviPMiKFox4Rc="),
        ("918237823721", "1BVtsOHoBuzlxmopndgjDnaamCMwGiAD8FtFQMgtoSpYnd_IDde2Qj4mbj6e0-KufVsIM0sEj6-dBLP0wEBOkTbYjPc8aEYvm73ymi-rifEB7zzZH_khBTYZOBb22C9A7HM_T1RxCx9hTyZu54r9JiefoRlLpd-dbDlq4d_f9NzKKVvWibtNsgeQuEFF9ad4UXLEGD54-nTCrQpLGku2_sr5ocqjMZ6Cwb1LTgLrJIHzZXY7wzggJ3OGyG5Dx1WqbyujZLCpUuiaJShX9TFMI94JpqK1xIB0rB9VvWKzcVZliERkDtxanpeawFRUavsQx64O_Gu2VWbEA6M9N1T7PPTnw5TP4G7U="),
        ("918280808004", "1BVtsOHoBu72ATDLZ4iMhuSnjn1Me9K-lx09r7ubRATNZSJKo5L81uYhb_z2AOg_sNjpIPVjDYo_foHdx7wKkDd51Mg_O1Adq1M-V3xXw47okiC6F3fX6EFQwjcP7dzCDphDeLyUoUM4ik8Hj4k-ENzWOSMQJMGTCToNtYga3vMlcuOqREhMz3bWqeEnxoebMTekMjEvmWT4ho9hAvs8Tb7JRQT24VAknNHQQn9wmGDcU_HftKE3aZBuTsXWnCQgr7rHxyBDbB3OL-Olv0HwCfcR-PDgvmZk48p6FwfPjG0PO5qzf6qhSxMoEIviWB3K1afQn9YTyRwDh8k6WV44UjRpZjJvbZsk="),
        ("918186972777", "1BVtsOHoBu5xUh_pg9AJqqdkFIrRguPcb2CZpMYAlI4286KA9HbZ9nuZiWani5QFi8s-xCL3oR5Q53eROtAnLi4iAx73UQUPunQLsk5qSmQD22WXA3-SoIXMnl-NetQ03wstekpbDk10_QUTF0OUE8_QGptuXkfhc3nlrUPJkqshq5aY6ehZVuYg4ErASwyy9w4aVWXKUvR6yhogE3k1RgaYURwSMHsmYyzqDxwXQ8CLSKFX543kErMdzY_9bOilpmnND5lGcnrqgoKebS5pJtBxbg9NiTQtwPtG_Ao3WG5tMCAZLVJLvCRXPuM5zK6C8J8AI_9FvCyLbSKJlYjW6qjb9iTnSNTY="),
        ("918208821367", "1BVtsOHoBu0FmVcgXO4y6fVhOJ-VIbEucy9H6wPhYnroRMyIshTVApooArU9FUyM9wv_2yjKFanaeyLSdXv1bT4wycxEFdi_EzsUG5tB5xpARqtiRjmtDyV9o4JS-ugXKwZR5BDHgl_nQb2vwZXu4GWpnFsc08tLOYO1czCOf9MyRUhqRKBh5OmQIRZJbo7MMSkQq_Ee1xBZ0L549vbqNboynMhAoWNB2madBdVi398C7JOmTLa-HTjo8NylsuV0pTwECa69DIDJex9QT5l5a2UFHzhjWT_qfNz0ewSvpnTQFA1ClGLV9fKfEaHkEYgvUsKsZ-KuvUQd9_WQUbn7c230KIlzXj20="),
        ("918260962457", "1BVtsOHoBu7FiKzEa1hePi2DYn9H0Mc40IL0rrKwJxB0LyHy0E9rpDMBsbiSJKDKmeDABqjSuuy_A0aQHY3y6JT-MxpmZ55ntcNzruLmtA9IxkXQtD4evfPp4DhOKVoM_CRpsIMO6czSv6YFsRRQHiNDdIZfN6oa6KnxSowrfwpe357LJGUmCzmtYbVtM84OPLtOpawCmmclfb36VnzcJmNCVo-sxMZAc-6R-o_PM15f9h4iW7SB-5klGY2DYcdUMP4hc_AITlvZ3BIC5Lfg9Yw0kTe-qv8lKyPBc3LZQcNRq7YDuD-KMgTcSE1HfmEKVLXie-1eVhDzBE3BMUk_-6eUwhg5E85Y="),
        ("918220190406", "1BVtsOHoBu2JlO5xTdTmdndzo2k5S-BHDjzkJecd7tDR8fgrzWWhXRJjzKxj1og323lh4-qYNTRPcZZ4vpLZwo2fE4gFE65q2pUeC9NNFXoGTtXo_4JP7ZBqW6wwPX-jrxnWTtBig_l_z7U4_qsD8kmQobNXMfE5J_Sn1Nk9ekzEICOHh0i9WIQFLlJl98RCG-_iEqv8pSIYjiSUDrPEDADhi1k9LYrzzN6IBAKbXCu-VUoLbZofPBZnKy5zIsarDdLM6qi_0fpkthxGZWtrbgOPf6ngTzo6B20XCQgKd2zYy4HyVzhpRk3zRZqyYyVFN8heTYYo-Iy9nESaXk3Ad3C9n6fTVmzM="),
        ("918281592533", "1BVtsOHoBux8yBCgA8mp0Y12_aCmVcgp7nxKlYHx93Gi7BTiEaT56ts_KTslhwU4xGPz0M7SnBxy-jdYr7GtruiIDYW2b8O1FQbYtvql151cJk4ZLfx4plBbXyGD4e_No_E_RrpBgk24UrRb42ZbEj-MC8snEB9Iv5M46LdKOksoYBENpxVOSr9AgqmVmmYaestW-2BxKFB1WPJCsm9W1PAWxOLGiPqW_-8Sscbz9GNBFJEnYFeEA2a7ZgBB30LENnBzm25-x7h79pBwGyCW3JXtog65sbzkebfE-oFaSeKAep4QbB4X2qXbWm7dywkdEQpNiPuP93bwfx4C49dPidAww6vPiRak="),
        ("918177862609", "1BVtsOHoBu61SCq0k5qkcxc-iY5INPc_6eHI_PgsmnrOJMqZt5bP7kO_bIciESKf3XtHzVB5fc_Y7YII04C2jacJpVxGPCmoZPJbhcKOTQqwFAUV3i5QZATb853imWqu2lT81t8f4iNv1rG6DdpnvehE5_fEyY3k3oVqiu2W4PbNlXeL9X7lfxEFsQxNTM_aP23hA4FRlAFZYsapnZiDseiB0X0-CNpY-AA91pkxMWqu2wgLjcw1jGDoJzT9FK8B9N1dzbs_-qo9WBbtJsHBxJ8cC7HuK0STtBPAXjwH9eDQBvRWVOJMuzhtXa5nrtRzv5Q7GVhOjWSaAKXCUOC49arwBIuae9cs=")
    ]

    print(f"🚀 Starting bulk import of {len(accounts_to_add)} accounts...")
    
    success_count = 0
    for phone, session in accounts_to_add:
        try:
            # Normalize phone: Ensure it starts with + if not present
            if not phone.startswith('+'):
                phone = "+" + phone
                
            # Normalize session: Remove any whitespace or newlines
            session = session.strip()
            
            # Use existing helper to add account manually
            # This sets seller_id to 0 (admin/system) and price to 0.00
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