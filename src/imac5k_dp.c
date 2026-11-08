// SPDX-License-Identifier: GPL-2.0-or-later
#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt

#include <linux/dmi.h>
#include <linux/kprobes.h>
#include <linux/module.h>
#include <linux/string.h>
#include <linux/uaccess.h>
#include <drm/display/drm_dp.h>
#include <drm/display/drm_dp_helper.h>

#define AUX_NAME_PREFIX "AMDGPU"

static bool force;
module_param(force, bool, 0444);
MODULE_PARM_DESC(force, "Activate even if the DMI product is not iMac15,1");

static atomic_t suppressed = ATOMIC_INIT(0);
module_param_named(suppressed, suppressed.counter, int, 0444);
MODULE_PARM_DESC(suppressed, "Number of DP sink D3 transitions suppressed (read-only)");

static const u8 power_d0 = DP_SET_POWER_D0;
static bool armed;

static int dpcd_write_pre(struct kprobe *p, struct pt_regs *regs)
{
	/* x86-64 SysV: (aux, offset, buffer, size) in rdi, esi, rdx, rcx. */
	const struct drm_dp_aux *aux = (const struct drm_dp_aux *)regs->di;
	const u8 *buf = (const u8 *)regs->dx;
	const char *name;
	char prefix[sizeof(AUX_NAME_PREFIX) - 1];
	u8 val;

	if ((u32)regs->si != DP_SET_POWER || regs->cx != 1 || !aux || !buf)
		return 0;
	if (get_kernel_nofault(val, buf) || (val & DP_SET_POWER_MASK) != DP_SET_POWER_D3)
		return 0;
	if (get_kernel_nofault(name, &aux->name) || !name ||
	    copy_from_kernel_nofault(prefix, name, sizeof(prefix)) ||
	    memcmp(prefix, AUX_NAME_PREFIX, sizeof(prefix)))
		return 0;

	regs->dx = (unsigned long)&power_d0;
	atomic_inc(&suppressed);
	return 0;
}

static struct kprobe kp = {
	.symbol_name = "drm_dp_dpcd_write",
	.pre_handler = dpcd_write_pre,
};

static int __init imac5k_dp_init(void)
{
	const char *product = dmi_get_system_info(DMI_PRODUCT_NAME);
	int ret;

	if (!force && (!product || strcmp(product, "iMac15,1"))) {
		pr_info("not an iMac15,1 (%s), staying idle\n", product ?: "?");
		return 0;
	}

	ret = register_kprobe(&kp);
	if (ret) {
		pr_err("cannot probe %s: %d\n", kp.symbol_name, ret);
		return ret;
	}
	armed = true;
	pr_info("armed on %pS\n", kp.addr);
	return 0;
}

static void __exit imac5k_dp_exit(void)
{
	if (armed)
		unregister_kprobe(&kp);
}

module_init(imac5k_dp_init);
module_exit(imac5k_dp_exit);
MODULE_SOFTDEP("pre: drm_display_helper");
MODULE_DESCRIPTION("Keep iMac15,1 5K panel DP receivers powered under amdgpu");
MODULE_LICENSE("GPL");
